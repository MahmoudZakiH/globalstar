# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import ValidationError


class StockPickingGlobalLandCosts(models.Model):
    _inherit = 'stock.picking'

    landed_cost_id = fields.Many2one(comodel_name="stock.landed.cost")

    def get_land_costs(self):
        if not self.landed_cost_id:
            self.landed_cost_id = self.env['stock.landed.cost'].create({'picking_ids': [(4, self.id)]}).id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Landed Costs'),
            'res_model': 'stock.landed.cost',
            'view_mode': 'form',
            'res_id': self.landed_cost_id.id
        }


class PurchaseOrderGlobalLandedCost(models.Model):
    _inherit = 'purchase.order'

    is_landed_cost = fields.Boolean()

    def _get_landed_cost(self):
        for rec in self:
            # rec.is_landed_cost = False
            for receipt in rec.picking_ids:
                if receipt.landed_cost_id:
                    if receipt.landed_cost_id.state == 'done':
                        rec.is_landed_cost = True

    def action_create_invoice(self):
        for rec in self:
            rec._get_landed_cost()
            if not rec.is_landed_cost:
                raise ValidationError(_("Please create Landed Cost from receipts first and validate it"))
        return super(PurchaseOrderGlobalLandedCost, self).action_create_invoice()
