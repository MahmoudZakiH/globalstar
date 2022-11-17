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
                total_cost += line.product_total_cost
            rec.total_products_cost = total_cost

    def _calc_total_profit(self):
        for rec in self:
            rec.total_profit = rec.amount_untaxed_signed - rec.total_products_cost


class AccountMoveLineGlobalProfit(models.Model):
    _inherit = 'account.move.line'

    product_cost = fields.Float(string="Cost",  readonly=1)
    product_total_cost = fields.Float(string="Total Cost",  readonly=1)
    product_profit = fields.Float(string="Profit",  readonly=1)
    product_total_profit = fields.Float(string="Total Profit",  readonly=1)
    move_type = fields.Selection(related='move_id.move_type')
    invoice_user_id = fields.Many2one('res.users', string='Salesperson', related="move_id.invoice_user_id", store=1)
    invoice_date_due = fields.Date(string='Due Date', related="move_id.invoice_date_due")

    @api.onchange('product_id', 'quantity', 'price_unit')
    @api.constrains('product_id', 'quantity', 'price_unit')
    def calc_product_cost(self):
        for rec in self:
            rec.product_cost = 0
            rec.product_total_cost = 0
            if rec.product_id:
                if rec.product_id.detailed_type == 'product':
                    rec.product_cost = rec.product_id.standard_price
                    rec.product_total_cost = rec.product_id.standard_price * rec.quantity
            if rec.move_id:
                rec.move_id.calc_total_products_cost()
            rec.product_profit = rec.price_unit - rec.product_cost
            rec.product_total_profit = rec.product_profit * rec.quantity
