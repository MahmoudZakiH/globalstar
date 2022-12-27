# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang, get_lang, format_amount

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

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        if not self.product_id or self.invoice_lines:
            return
        params = {'order_id': self.order_id}
        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and self.order_id.date_order.date(),
            uom_id=self.product_uom,
            params=params)

        if seller or not self.date_planned:
            self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # If not seller, use the standard price. It needs a proper currency conversion.
        if not seller:
            # po_line_uom = self.product_uom or self.product_id.uom_po_id
            # price_unit = self.env['account.tax']._fix_tax_included_price_company(
            #     self.product_id.uom_id._compute_price(self.product_id.standard_price, po_line_uom),
            #     self.product_id.supplier_taxes_id,
            #     self.taxes_id,
            #     self.company_id,
            # )
            # if price_unit and self.order_id.currency_id and self.order_id.company_id.currency_id != self.order_id.currency_id:
            #     price_unit = self.order_id.company_id.currency_id._convert(
            #         price_unit,
            #         self.order_id.currency_id,
            #         self.order_id.company_id,
            #         self.date_order or fields.Date.today(),
            #     )

            # self.price_unit = price_unit
            return

        # price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price, self.product_id.supplier_taxes_id, self.taxes_id, self.company_id) if seller else 0.0
        # if price_unit and seller and self.order_id.currency_id and seller.currency_id != self.order_id.currency_id:
            # price_unit = seller.currency_id._convert(
            #     price_unit, self.order_id.currency_id, self.order_id.company_id, self.date_order or fields.Date.today())

        # if seller and self.product_uom and seller.product_uom != self.product_uom:
        #     price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)

        # self.price_unit = price_unit

        default_names = []
        vendors = self.product_id._prepare_sellers({})
        for vendor in vendors:
            product_ctx = {'seller_id': vendor.id, 'lang': get_lang(self.env, self.partner_id.lang).code}
            default_names.append(self._get_product_purchase_description(self.product_id.with_context(product_ctx)))

        if (self.name in default_names or not self.name):
            product_ctx = {'seller_id': seller.id, 'lang': get_lang(self.env, self.partner_id.lang).code}
            self.name = self._get_product_purchase_description(self.product_id.with_context(product_ctx))


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
