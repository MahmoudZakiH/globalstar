# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class StockPickingDistributionLocations(models.Model):
    _name = 'stock_picking.distribution_locations'

    def get_locations(self):
        locations = self.env['stock.location'].sudo().search_read(
            [('usage', '=', 'internal'), ('internal_transit', '=', True)], ['name', 'location_id'])
        locations_list = []
        for l in locations:
            locations_list.append((str(l['id']), l['location_id'][1] + '/' + l['name']))
        return locations_list

    product_id = fields.Many2one(comodel_name="product.product", required=1)
    picking_id = fields.Many2one(comodel_name="stock.picking")
    location_id = fields.Selection(selection=get_locations, required=1)
    quantity = fields.Float()
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number', domain="[('product_id', '=', product_id)]")


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
            products = rec.distribution_location_ids.mapped('product_id')
            for product in products:
                if sum(rec.distribution_location_ids.filtered(lambda p: p.product_id.id == product.id).mapped(
                        'quantity')) > sum(
                        rec.move_ids_without_package.filtered(lambda p: p.product_id.id == product.id).mapped(
                                'quantity_done')):
                    raise UserError(_('Sorry, The quantity to be transferred is greater than the quantity transferred'))

            transfer_location = self.env['stock.location'].search(
                [('usage', '=', 'transit'), ('company_id', '=', False)], limit=1)
            if not transfer_location:
                raise UserError(_('Sorry, No Transit Location Available'))
            if rec.picking_type_code == 'incoming':
                transfer_lines = []
                products = rec.distribution_location_ids.mapped('product_id')
                internal_transit = self.env['stock.picking.type'].search(
                    [('default_location_src_id', '=', rec.location_dest_id.id), ('internal_transit', '=', True)],
                    limit=1)
                if not internal_transit:
                    raise UserError(_('Sorry, No Internal Transit Operation Available'))
                for product in products:
                    products_lines = rec.distribution_location_ids.filtered(lambda p: p.product_id.id == product.id)
                    lots = products_lines.mapped('lot_id')
                    for lot in lots:
                        quantity = sum(products_lines.filtered(lambda p: p.lot_id.id == lot.id).mapped('quantity'))
                        transfer_lines.append(self.env['stock.move'].create({
                            'product_id': product.id,
                            'name': product.name,
                            'product_uom': product.uom_id.id,
                            'product_uom_qty': quantity,
                            'show_details_visible': True,
                            'lot_ids': [(4, lot.id)],
                            'location_id': rec.location_dest_id.id,
                            'location_dest_id': transfer_location.id,
                        }).id)
                transfer_id = self.env['stock.picking'].create({
                    'picking_type_id': internal_transit.id,
                    'location_id': rec.location_dest_id.id,
                    'location_dest_id': transfer_location.id,
                    'origin': rec.name,
                    'move_ids_without_package': [(6, 0, transfer_lines)]
                })
                transfer_id.sudo().action_confirm()
                transfer_id.move_line_ids_without_package.unlink()
                move_line_ids_without_package = []
                for move in transfer_id.move_ids_without_package:
                    for product in products:
                        products_lines = rec.distribution_location_ids.filtered(lambda p: p.product_id.id == product.id == move.product_id.id)
                        lots = products_lines.mapped('lot_id')
                        for lot in lots:
                            quantity = sum(products_lines.filtered(lambda p: p.lot_id.id == lot.id).mapped('quantity'))
                            move_line_ids_without_package.append((0, 0, {
                                    'move_id': move.id,
                                    'product_id': product.id,
                                    'product_uom_id': product.uom_id.id,
                                    'product_uom_qty': 0,
                                    'qty_done': quantity,
                                    'lot_id': lot.id,
                                    'location_id': rec.location_dest_id.id,
                                    'location_dest_id': transfer_location.id,
                                }))
                transfer_id.move_line_ids_without_package = move_line_ids_without_package
                transfer_id.sudo().button_validate()

            locations = []
            for location in rec.distribution_location_ids:
                if int(location.location_id) not in locations:
                    locations.append(int(location.location_id))
            for location in locations:
                internal_transit = self.env['stock.picking.type'].sudo().search(
                    [('default_location_dest_id', '=', int(location)), ('internal_transit', '=', True)],
                    limit=1)
                if not internal_transit:
                    raise UserError(_('Sorry, No internal transit operation available for some locations'))
                transfer_lines = []
                for line in rec.distribution_location_ids.filtered(lambda l: int(l.location_id) == int(location)):
                    transfer_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.product_id.name,
                        'company_id': internal_transit.company_id.id,
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
                picking.sudo().action_confirm()
            rec.is_transferred = True


class PickingTypeDistribution(models.Model):
    _inherit = 'stock.picking.type'

    internal_transit = fields.Boolean()


class PickingLocationDistribution(models.Model):
    _inherit = 'stock.location'

    internal_transit = fields.Boolean()
