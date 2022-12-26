# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

SPLIT_METHOD = [
    ('equal', 'Equal'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
]

class PartnerGlobal(models.Model):
    _inherit = 'res.partner'

    contact_person_id = fields.Many2one(comodel_name="res.users", default=lambda self: self.env.user)
    c_r = fields.Char(string="C.R #")
    nickname = fields.Char()
    credit_limit = fields.Float()


class SaleOrderGlobal(models.Model):
    _inherit = 'sale.order'

    credit_limit_available = fields.Float(compute='_calc_credit_limit_available')

    def action_confirm(self):
        for rec in self:
            if (rec.credit_limit_available - rec.amount_total) < 0:
                raise UserError(_('sorry, your credit limit is not enough'))
        return super(SaleOrderGlobal, self).action_confirm()

    def _calc_credit_limit_available(self):
        for rec in self:
            if rec.partner_id:
                rec.credit_limit_available = rec.partner_id.credit_limit - rec.partner_id.total_due


class AccountPaymentGlobal(models.Model):
    _inherit = 'account.payment'

    allow_journal_ids = fields.Many2many('account.journal', compute='_compute_allow_journal_ids',
                                         relation="journal_payments_rel")

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_allow_journal_ids(self):
        for m in self:
            domain = [('type', 'in', ('bank', 'cash'))]
            if self.env.user.account_journal_ids:
                domain.append(('id', 'in', self.env.user.account_journal_ids.ids))
            m.allow_journal_ids = self.env['account.journal'].search(domain)


class AccountMoveGlobal(models.Model):
    _inherit = 'account.move'

    @api.model
    def _search_default_journal(self, journal_types):
        company_id = self._context.get('default_company_id', self.env.company.id)
        domain = [('company_id', '=', company_id), ('type', 'in', journal_types)]
        if self.env.user.account_journal_ids:
            domain.append(('id', 'in', self.env.user.account_journal_ids.ids))

        journal = None
        if self._context.get('default_currency_id'):
            currency_domain = domain + [('currency_id', '=', self._context['default_currency_id'])]
            journal = self.env['account.journal'].search(currency_domain, limit=1)

        if not journal:
            journal = self.env['account.journal'].search(domain, limit=1)

        if not journal:
            company = self.env['res.company'].browse(company_id)

            error_msg = _(
                "No journal could be found in company %(company_name)s for any of those types: %(journal_types)s",
                company_name=company.display_name,
                journal_types=', '.join(journal_types),
            )
            raise UserError(error_msg)

        return journal

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_id = m.company_id.id or self.env.company.id
            domain = [('company_id', '=', company_id), ('type', '=', journal_type)]
            if self.env.user.account_journal_ids:
                domain.append(('id', 'in', self.env.user.account_journal_ids.ids))
            m.suitable_journal_ids = self.env['account.journal'].search(domain)


class ResUsersGlobal(models.Model):
    _inherit = 'res.users'

    stock_warehouse_ids = fields.Many2many(comodel_name="stock.warehouse", relation="warehouse_user_rel")
    account_journal_ids = fields.Many2many(comodel_name="account.journal", relation="journal_user_rel")

    @api.constrains('stock_warehouse_ids')
    def onchange_stock_warehouse(self):
        self.clear_caches()


class AccountJournalGlobal(models.Model):
    _inherit = 'account.journal'

    specific_users_ids = fields.Many2many(comodel_name="res.users", relation="journal_user_rel", string="Users")


class PurchaseOrderLineGlobal(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_id')
    def set_product_price_unit(self):
        for rec in self:
            rec.price_unit = 0


class StockMoveLineGlobal(models.Model):
    _inherit = 'stock.move.line'

    container_number = fields.Char(string="Container Number")


class StockLandedCostLines(models.Model):
    _inherit = 'stock.landed.cost.lines'

    split_method = fields.Selection(
        SPLIT_METHOD,
        string='Split Method',
        default='by_weight',
        readonly=1,
        required=True,
        help="Equal : Cost will be equally divided.\n"
             "By Quantity : Cost will be divided according to product's quantity.\n"
             "By Current cost : Cost will be divided according to product's current cost.\n"
             "By Weight : Cost will be divided depending on its weight.\n"
             "By Volume : Cost will be divided depending on its volume.")
