# -*- coding: utf-8 -*-

from odoo import models, fields, api , _
from odoo.exceptions import ValidationError, UserError

from odoo.tools import float_is_zero
from collections import defaultdict




class SaleOrderLineGlobal(models.Model):
    _inherit = 'sale.order.line'

    state_type = fields.Selection(string="Type", selection=[('normal', 'Normal'), ('auction', 'Auction'), ],
                                  required=False,related='order_id.state_type' ,store=True)

    product_id = fields.Many2one(
        'product.product', string='Product',
        domain=lambda self: "[('id','in',%s),('sale_ok', '=', True)]" % (self.env['product.product'].search([('is_great_a','=',True)]).ids if self.state_type == 'normal' else self.env['product.product'].search([('is_great_b','=',True)]).ids ), change_default=True, ondelete='restrict', check_company=True)

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLineGlobal, self)._prepare_invoice_line()
        for move in self.move_ids:
            line = move.move_line_ids.filtered(lambda p: p.product_id.id == self.product_id.id)
            res['lot_id'] = line.lot_id.id if line else False
        return res

    @api.onchange('discount')
    def limit_discount_type(self):
        for rec in self:
            if rec.discount > rec.product_id.limit_discount:
                raise UserError('limit discount should be less .')

    @api.onchange('state_type')
    def domain_state_type(self):
        for rec in self:
            if rec.state_type:
                if rec.state_type == 'normal':
                    return {'domain': {
                        'product_id': [('is_great_a', '=', True)]
                    }}
                else:

                    return {'domain': {'product_id': [('is_great_b', '=', True)]}}
            else:
                return {'domain': {'product_id': [('id', 'in', 0)]}}


class SaleOrder(models.Model):
    _inherit = 'sale.order'




    state_type = fields.Selection(string="Type", selection=[('normal', 'Normal'), ('auction', 'Auction'), ], required=True, default="normal" )



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_consignment = fields.Boolean(string="Is Consignment",  )
    is_great_a = fields.Boolean(string="Grade A",  )
    is_great_b = fields.Boolean(string="Grade B",  )
    limit_discount = fields.Float(string="Limit Discount",  required=False, )



class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_consignment = fields.Boolean(string="Is Consignment",  )
    is_great_a = fields.Boolean(string="Grade A", )
    is_great_b = fields.Boolean(string="Grade B", )
    limit_discount = fields.Float(string="Limit Discount", required=False, )


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_consignment = fields.Boolean(string="Is Consignment",  )




class AccountAccount(models.Model):
    _inherit = 'account.account'

    is_consignment = fields.Boolean(string="Is Consignment",  )




class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial Number',
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]", check_company=True, )






class AccountMove(models.Model):
    _inherit = 'account.move'


    consignment_id = fields.Many2one(comodel_name="account.move", string="Consignment", required=False, )



    def button_draft(self):
        res=super(AccountMove, self).button_draft()
        consignments = self.env['account.move'].sudo().search([('consignment_id','=',self.id)])
        for rec in consignments:
            rec.button_cancel()
        return res


    def test_get_invoiced_lot_values(self):
        for rec in self:
            rec._get_invoiced_lot_values()

    def _get_invoiced_lot_values(self):
        res = super(AccountMove, self)._get_invoiced_lot_values()
        if res:
            for line in res:
                line['product_id'] = self.env['stock.production.lot'].sudo().search([('id','=',int(line['lot_id']))],limit=1).product_id.id

        return res




    def git_invoices_consignment(self):
        for rec in self:
            return {
                'name': 'Entry',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('consignment_id', '=', self.id)],
            }


    def action_post(self):
        res=super(AccountMove, self).action_post()
        for rec in self:
            rec.get_create_entry_consignment()
        return res




    def get_create_entry_consignment(self):
        for rec in self:
            vendor=0
            values = rec._get_invoiced_lot_values()
            for line in rec.invoice_line_ids:
                if line.product_id.is_consignment:
                    if values:
                        for value in values:

                            if value['product_id'] == line.product_id.id and value['lot_id']:
                                lot=self.env['stock.production.lot'].sudo().search([('id','=',int(value['lot_id']))],limit=1)
                                line.lot_id=lot.id
                                vendor = lot.vendor_id
                    if vendor:
                        amount = line.price_unit * line.quantity * 93 / 100
                        entry = self.env['account.move'].sudo().create({
                            'move_type': 'entry',
                            'ref': rec.name,
                            'date': fields.date.today(),
                            'journal_id': self.env['account.journal'].sudo().search([('is_consignment','=',True), ('company_id','=', rec.company_id.id)],limit=1).id if self.env['account.journal'].sudo().search([('is_consignment','=',True), ('company_id','=', rec.company_id.id)],limit=1) else False ,
                            'line_ids': [(0, 0, {
                                'account_id': self.env['account.account'].sudo().search([('is_consignment','=',True), ('company_id','=', rec.company_id.id)],limit=1).id if self.env['account.account'].sudo().search([('is_consignment','=',True), ('company_id','=', rec.company_id.id)],limit=1) else False ,
                                # 'partner_id': vendor.id,
                                'name': 'Consignment',
                                'debit': amount,
                            }), (0, 0, {
                                'account_id': vendor.property_account_payable_id.id,
                                'partner_id': vendor.id,
                                # 'name': rec.employee_id.name,
                                'credit': amount,
                            })],
                        })
                        entry.consignment_id = rec.id
                        entry.action_post()
                    else:
                        raise UserError(_('Product %s has not vendor .', line.product_id.name))





class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    seq = fields.Integer(string="Sequence", required=False,default=0 )
    vendor_id = fields.Many2one(comodel_name="res.partner", string="Vendor", required=False, store=True,)





class StockMove(models.Model):
    _inherit = 'stock.move'



    vendor_id = fields.Many2one(comodel_name="res.partner", string="Vendor", required=False,store=True , related='picking_id.partner_id' )


    def button_create_lot(self):
        for rec in self:
            lines=[]
            old_sequence = self.env['stock.production.lot'].sudo().search([('product_id','=',rec.product_id.id)],).mapped('seq')
            if old_sequence :
                old_sequence = max(old_sequence) + 1
            else:
                old_sequence = 1
            if rec.move_line_nosuggest_ids:
                for line in rec.move_line_nosuggest_ids:
                    if not line.lot_id:
                        if len(str(old_sequence)) <= 4:
                            sequence = str(rec.product_id.default_code[0:4] if rec.product_id.default_code else '') + '/' + str(rec.picking_id.scheduled_date.date()) + '/' + (4 - len(str(old_sequence))) * '0' + str(old_sequence)
                            lot=self.env['stock.production.lot'].sudo().create({
                                'name' : sequence,
                                'product_id' : rec.product_id.id ,
                                'vendor_id' : rec.picking_id.partner_id.id ,
                                'seq' : old_sequence ,
                            })
                            line.lot_id = lot.id

            else:
                if len(str(old_sequence)) <= 4:
                    sequence = str(rec.product_id.default_code[0:4] if rec.product_id.default_code else '') + '/' + str(rec.picking_id.scheduled_date.date()) + '/' + (4 - len(str(old_sequence))) * '0' + str(old_sequence)
                    lot=self.env['stock.production.lot'].sudo().create({
                        'name' : sequence,
                        'product_id' : rec.product_id.id ,
                        'vendor_id' : rec.picking_id.partner_id.id ,
                        'seq' : old_sequence ,
                    })

                    lines.append([0, 0,{
                        'product_id': rec.product_id.id,
                        'location_dest_id' : rec.location_dest_id.id,
                        'lot_id' : lot.id,
                        'product_uom_id': rec.product_uom.id,
                    }])
                    rec.move_line_nosuggest_ids = lines
