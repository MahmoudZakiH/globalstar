# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import ValidationError


class PartnerGlobal(models.Model):
    _inherit = 'res.partner'

    invoice_percentage = fields.Float()


class AccountMoveGlobal(models.Model):
    _inherit = 'account.move'

    discount_move_id = fields.Many2one(comodel_name="account.move")

    def action_post(self):
        super(AccountMoveGlobal, self).action_post()
        for rec in self:
            debit_disc = self.env['account.account'].search_read(
                [('customer_discount', '=', 'debit'), ('company_id', '=', rec.company_id.id)], fields=['id'],
                limit=1)
            credit_disc = self.env['account.account'].search_read(
                [('customer_discount', '=', 'credit'), ('company_id', '=', rec.company_id.id)], fields=['id'],
                limit=1)
            vat_disc = self.env['account.account'].search_read(
                [('customer_discount', '=', 'vat'), ('company_id', '=', rec.company_id.id)], fields=['id'],
                limit=1)
            journal = self.env['account.journal'].sudo().search([('partner_discount', '=', True), ('company_id', '=', rec.company_id.id)], limit=1)
            if not journal:
                raise ValidationError(_('Please Select Partner Discount In Journals First'))
            if debit_disc and credit_disc:
                if rec.move_type == 'out_invoice':
                    if rec.partner_id:
                        if rec.partner_id.invoice_percentage > 0:
                            disc = rec.partner_id.invoice_percentage * rec.amount_untaxed_signed / 100
                            vat = rec.partner_id.invoice_percentage * rec.amount_tax_signed / 100
                            lines = [(0, 0, {
                                    'name': _('Customer Discount'),
                                    'account_id': debit_disc[0]['id'],
                                    'debit': disc,
                                    'credit': 0,
                                    'is_partner_disc': True,
                                }), (0, 0, {
                                    'name': _('Customer Discount'),
                                    'account_id': credit_disc[0]['id'],
                                    'debit': 0,
                                    'credit': disc - vat,
                                    'is_partner_disc': True,
                                })]
                            if rec.amount_tax_signed > 0 and vat_disc:
                                lines.append((0, 0, {
                                    'name': _('Customer Discount'),
                                    'account_id': vat_disc[0]['id'],
                                    'debit': 0,
                                    'credit': vat,
                                    'is_partner_disc': True,
                                }))
                            disc_move = self.env['account.move'].create({
                                'move_type': 'entry',
                                'ref': rec.name,
                                'journal_id': journal.id,
                                'date': fields.date.today(),
                                'line_ids': lines,
                            })
                            rec.discount_move_id = disc_move.id
                            disc_move.action_post()

    def button_draft(self):
        super(AccountMoveGlobal, self).button_draft()
        for rec in self:
            if rec.move_type == 'out_invoice':
                rec.discount_move_id.unlink()

    def git_invoice_partner_discount(self):
        return {
            'name': 'Partner Discounts',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'res_id': self.discount_move_id.id,
        }


class AccountMoveLineGlobal(models.Model):
    _inherit = 'account.move.line'

    is_partner_disc = fields.Boolean()


class AccountAccountGlobal(models.Model):
    _inherit = 'account.account'

    customer_discount = fields.Selection(selection=[('debit', 'Debit'), ('credit', 'Credit'), ('vat', 'Vat')])


class AccountJournalGlobal(models.Model):
    _inherit = 'account.journal'

    partner_discount = fields.Boolean()
