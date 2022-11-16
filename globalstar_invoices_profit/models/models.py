# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMoveGlobalProfit(models.Model):
    _inherit = 'account.move'

    total_products_cost = fields.Float(string="Total Cost",  readonly=1)
    total_profit = fields.Float(string="Total Profit",  compute='_calc_total_profit')

    @api.constrains('invoice_line_ids')
    def calc_total_products_cost(self):
        for rec in self:
            total_cost = 0
            for line in rec.invoice_line_ids:
                total_cost += line.product_cost
            rec.total_products_cost = total_cost

    def _calc_total_profit(self):
        for rec in self:
            rec.total_profit = rec.amount_untaxed_signed - rec.total_products_cost


class AccountMoveLineGlobalProfit(models.Model):
    _inherit = 'account.move.line'

    product_cost = fields.Float(string="Cost",  readonly=1)
    product_profit = fields.Float(string="Profit", compute='_calc_total_profit', store=True)
    move_type = fields.Selection(related='move_id.move_type')

    @api.onchange('product_id', 'quantity')
    @api.constrains('product_id', 'quantity')
    def calc_product_cost(self):
        for rec in self:
            rec.product_cost = 0
            if rec.product_id:
                if rec.product_id.detailed_type == 'product':
                    rec.product_cost = rec.product_id.standard_price * rec.quantity
            if rec.move_id:
                rec.move_id.calc_total_products_cost()

    @api.depends('product_id', 'quantity')
    def _calc_total_profit(self):
        for rec in self:
            rec.product_profit = rec.price_subtotal - rec.product_cost
