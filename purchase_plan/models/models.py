# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

MONTH_SELECTION = [
    ('1', 'January'),
    ('2', 'February'),
    ('3', 'March'),
    ('4', 'April'),
    ('5', 'May'),
    ('6', 'June'),
    ('7', 'July'),
    ('8', 'August'),
    ('9', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December'),
]


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    plan_id = fields.Many2one(comodel_name="purchase.plan", string="Plan", required=False, )


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    planned_unplanned = fields.Selection(string="Planned/Unplanned",
                                         selection=[('planned', 'Planned'), ('unplanned', 'UnPlanned'), ],
                                         required=False, default='unplanned')
    loading_date = fields.Date(string="Loading Date", required=False, )

    @api.onchange('date_planned', 'loading_date', 'payment_term_id', 'order_line', 'order_line.product_qty')
    def _onchange_plane_fields(self):
        for rec in self:
            for line in rec.order_line:
                line.plan_id.ordered_qty = line.product_qty
                line.plan_id.expected_arrival_date = rec.date_planned
                line.plan_id.loading_date = rec.loading_date
                line.plan_id.payment_term_id = rec.payment_term_id.id


class PurchasePlan(models.Model):
    _name = 'purchase.plan'
    _description = 'Purchase Plan'

    name = fields.Char(string="Name", required=False, copy=False, default='New')
    sequence = fields.Integer(string="seq", required=False,default=0 )

    month = fields.Selection(MONTH_SELECTION, required=True)  # ,default=str(fields.Date.today().month)

    def _get_years(self):
        return [(str(i), i) for i in range(fields.Date.today().year + 5, fields.Date.today().year - 50, -1)]

    year = fields.Selection(
        selection='_get_years', string='Year', required=True, )

    # default=lambda x: str(fields.Date.today().year))

    def _get_weeks(self):
        return [(str(i), 'Week ' + str(i)) for i in range(1, 53)]

    week = fields.Selection(
        selection='_get_weeks', string='Week', required=True, )
    partner_id = fields.Many2one(comodel_name="res.partner", string="Supplier", required=True, )
    origin = fields.Char(string="Origin", required=False, )
    categ_id = fields.Many2one(comodel_name="product.category", string="Product Category", required=True, )
    product_id = fields.Many2one(comodel_name="product.product", string="Product", required=True,
                                 domain="[('categ_id', '=', categ_id)]")
    planned_qty = fields.Float(string="Planned Qty", required=True, )
    uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure', required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    expected_cost = fields.Float(string="Expected Cost", required=False, )
    historical_actual_cost = fields.Float(string="Historical Actual Cost", store=True, readonly=False, required=False,
                                          related='product_id.standard_price')
    purchase_id = fields.Many2one(comodel_name="purchase.order", string="Purchase", required=False, )
    po_date = fields.Date(string="Po Date", required=False, )
    confirm_date = fields.Datetime(string="Confirm Date", required=False,related='purchase_id.date_approve' )
    # po_state = fields.Char(string="Po State", required=False,related='purchase_id.state' )
    po_state = fields.Selection(string="Po State", selection=[('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'), ], required=False,related='purchase_id.state' )
    ordered_qty = fields.Float(string="Ordered Qty", required=False, )
    expected_arrival_date = fields.Datetime(string="Expected Arrival Date", required=False, )
    actual_arrival_date = fields.Datetime(string="Actual Arrival Date", required=False,related='purchase_id.effective_date' )
    loading_date = fields.Date(string="Loading Date", required=False, )
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', readonly=False)
    avg_die = fields.Integer(string="Avg Die", required=False, )
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    po_date_week_num = fields.Integer(string="Po Date Week Number", compute='_compute_po_date_week_num')
    actual_cost_currency = fields.Float(string="Historical Actual Cost In Currency", compute='_compute_historical_actual_cost_currency')

    @api.depends('historical_actual_cost')
    def _compute_historical_actual_cost_currency(self):
        for rec in self:
            rec.actual_cost_currency = 0
            if rec.historical_actual_cost != 0 and rec.currency_id:
                rec.actual_cost_currency = rec.historical_actual_cost / rec.currency_id.rate

    @api.depends('po_date')
    def _compute_po_date_week_num(self):
        for rec in self:
            rec.po_date_week_num = 0
            if rec.po_date:
                rec.po_date_week_num = rec.po_date.isocalendar()[1]

    @api.model
    def create(self, vals):
        res = super(PurchasePlan, self).create(vals)
        for rec in res:
            plans=self.env['purchase.plan'].sudo().search([],).mapped('sequence')
            print('plans',plans)
            max_plan=max(plans)
            rec.sequence = max_plan + 1
            rec.get_name()
        return res

    @api.onchange('month', 'year')
    def get_name(self):
        for rec in self:
            if rec.month and rec.year:
                month=dict(self._fields['month'].selection).get(self.month)
                if len(str(rec.sequence)) <= 6:
                    print('rec.month',rec.month)
                    rec.name = rec.year + '/' + month + '/' + (6 - len(str(rec.sequence))) * '0' + str(rec.sequence)
                else:
                    raise UserError(("The sequence must not exceed six numbers"))

    def create_purchase_order(self):
        vendor = []
        order_linee = []
        for rec in self:
            if rec.partner_id.id not in vendor:
                vendor.append(rec.partner_id.id)
        print('vvvvvvvvvv', vendor)
        if len(vendor) > 1:
            raise UserError("Warning , Please choose one vendor")
        if len(self.mapped('currency_id')) > 1:
            raise UserError("Warning , There are purchase plan have a different currency")
        for rec in self:
            if rec.purchase_id:
                raise UserError("Warning , There are purchase plan have a purchase order")
            order_linee.append((0, 0, {
                'plan_id': rec.id,
                'product_id': rec.product_id.id,
                'name': rec.product_id.name,
                'product_qty': rec.planned_qty,
                'product_uom': rec.uom_id.id,
                'date_planned': fields.datetime.now(),
                # 'attachmentt_ids': [a.id for a in line.attachment_ids],
                # 'purchase_requests_id': self.id,
                # 'purchase_request_line': [line.id],

            }))
        purchase_order = self.env['purchase.order'].sudo().create({
            "order_line": order_linee,
            "partner_id": vendor[0],
            "planned_unplanned": 'planned',
            "currency_id": self[0].currency_id.id,

        })
        print('purchase_order', purchase_order)
        for rec in self:

            rec.purchase_id = purchase_order.id
            rec.po_date = fields.date.today()
            rec.ordered_qty = rec.planned_qty
            rec.expected_arrival_date = purchase_order.date_planned
            rec.loading_date = purchase_order.loading_date
            rec.po_state = purchase_order.state
            rec.payment_term_id = purchase_order.payment_term_id.id

        # return {
        #     'name': 'R F Q',
        #     'res_model': 'purchase.order',
        #     'res_id': purchase_order.id,
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'form',
        #     # 'context': {
        #     #     "default_order_line": order_linee,
        #     #     "default_partner_id": vendor[0],
        #     #     "default_planned_unplanned": 'planned',
        #     #
        #     # },
        #     'target': 'new',
        # }
