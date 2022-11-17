# -*- coding: utf-8 -*-

from odoo import models, fields, _


class StockPickingDistributionLocations(models.Model):
    _name = 'stock_picking.distribution_locations'

    def get_locations(self):
        locations = self.env['stock.location'].sudo().search_read([('usage', '=', 'internal')], ['name', 'location_id'])
        locations_list = []
        for l in locations:
            locations_list.append((str(l['id']), l['location_id'][1] + '/' + l['name']))
        return locations_list

    product_id = fields.Many2one(comodel_name="product.product", required=1)
    picking_id = fields.Many2one(comodel_name="stock.picking")
    location_id = fields.Selection(selection=get_locations, required=1)
    quantity = fields.Float()


class StockPickingDistribution(models.Model):
    _inherit = 'stock.picking'

    distribution_location_ids = fields.One2many(comodel_name="stock_picking.distribution_locations",
                                                inverse_name="picking_id")
    products_domain_ids = fields.Many2many(comodel_name="product.product", compute='_get_products_domain')
    is_transferred = fields.Boolean()

    def _get_products_domain(self):
        for rec in self:
            products = []
            for line in rec.move_ids_without_package:
                products.append(line.product_id.id)
            rec.products_domain_ids = [(6, 0, products)]

    def distribution_locations(self):
        for rec in self:
            transfer_location = self.env['stock.location'].search(
                [('usage', '=', 'transit'), ('company_id', '=', False)], limit=1)
            if not transfer_location:
                raise ValueError(_('Sorry, No Transit Location Available'))
            if rec.picking_type_code == 'incoming':
                transfer_lines = []
                products = rec.distribution_location_ids.mapped('product_id')
                internal_transit = self.env['stock.picking.type'].search(
                    [('default_location_src_id', '=', rec.location_dest_id.id), ('internal_transit', '=', True)],
                    limit=1)
                if not internal_transit:
                    raise ValueError(_('Sorry, No Internal Transit Operation Available'))
                for product in products:
                    quantity = sum(
                        rec.distribution_location_ids.filtered(lambda p: p.product_id.id == product.id).mapped(
                            'quantity'))
                    transfer_lines.append((0, 0, {
                        'product_id': product.id,
                        'name': product.name,
                        'product_uom': product.uom_id.id,
                        'product_uom_qty': quantity,
                        'location_id': rec.location_dest_id.id,
                        'location_dest_id': transfer_location.id,
                    }))
                transfer_id = self.env['stock.picking'].create({
                    'picking_type_id': internal_transit.id,
                    'location_id': rec.location_dest_id.id,
                    'location_dest_id': transfer_location.id,
                    'origin': rec.name,
                    'move_ids_without_package': transfer_lines
                })
                transfer_id.action_confirm()
                transfer_id.button_validate()

            locations = []
            for location in rec.distribution_location_ids:
                if int(location.location_id) not in locations:
                    locations.append(int(location.location_id))
            for location in locations:
                internal_transit = self.env['stock.picking.type'].sudo().search(
                    [('default_location_dest_id', '=', int(location)), ('internal_transit', '=', True)],
                    limit=1)
                if not internal_transit:
                    raise ValueError(_('Sorry, No internal transit operation available for some locations'))
                transfer_lines = []
                for line in rec.distribution_location_ids.filtered(lambda l: int(l.location_id) == int(location)):
                    transfer_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.product_id.name,
                        'product_uom': line.product_id.uom_id.id,
                        'product_uom_qty': line.quantity,
                        'location_id': transfer_location.id,
                        'location_dest_id': int(location),
                    }))
                picking = self.env['stock.picking'].sudo().create({
                    'picking_type_id': internal_transit.id,
                    'location_id': transfer_location.id,
                    'location_dest_id': int(location),
                    'origin': rec.name,
                    'move_ids_without_package': transfer_lines
                })
                picking.action_confirm()
            rec.is_transferred = True


class PickingTypeDistribution(models.Model):
    _inherit = 'stock.picking.type'

    internal_transit = fields.Boolean()
