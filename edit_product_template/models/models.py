# -*- coding: utf-8 -*-

from odoo import models, fields, api



class ProductCategory(models.Model):
    _inherit = 'product.category'

    code = fields.Char(string="Code", required=False, )



class EditProductTemplate(models.Model):
    _inherit = 'product.template'




    variety_id = fields.Many2one(comodel_name="variety", string="Variety", required=False, )
    class_class = fields.Integer(string="Class", required=False, )
    size = fields.Char(string="Size", required=False, )
    origin_id = fields.Many2one(comodel_name="origin", string="Origin", required=False, )
    net_weight = fields.Float(string="Net Weight",  required=False, )
    brand = fields.Char(string="Brand", required=False, )
    type_id = fields.Many2one(comodel_name="type", string="Type", required=False, )
    purchase_indicator = fields.Selection(string="Purchase Indicator", selection=[('purchasable', 'Purchasable'), ('un_purchasable', 'UnPurchasable'), ], required=False, )
    serial_code = fields.Char(string="Serial Code", required=False,digits=(5, 2), )
    identification = fields.Char(string="Identification", required=False, )
    code = fields.Char(string="Code", required=False,copy=False )
    sequence = fields.Integer(string="Sequence", required=False,default=0,copy=False )




    def button_generate_name(self):
        for rec in self:
            if rec.origin_id:
                print('ddddddddddddddddddd',str(rec.origin_id.name[0:3]))
                rec.name=str(rec.categ_id.name)+' '+str(rec.variety_id.name)+' '+' - '+'class'+str(rec.class_class)+' - '+'size'+str(rec.size)+' - '+str(rec.origin_id.name[0:3]) +' - '+str(rec.uom_id.name)+str(rec.brand)+' - '+'A' if rec.is_great_a else 'B'
            else:
                rec.name=str(rec.categ_id.name)+' '+str(rec.variety_id.name)+' '+' - '+'class'+str(rec.class_class)+' - '+'size'+str(rec.size)+' - '+str(rec.uom_id.name)+str(rec.brand)+' - '+'A' if rec.is_great_a else 'B'
            if rec.is_great_a :
                rec.identification = 'A' + str(rec.type_id.name[0]) + str(rec.purchase_indicator[0]) + str(
                    rec.categ_id.code)
            elif rec.is_great_b:
                print('rec.type_id.name',rec.type_id.name)
                print(str(rec.type_id.name[0]),'str(rec.type_id.name[0])')
                rec.identification = 'B' + str(rec.type_id.name[0]) + str(
                    rec.purchase_indicator[0]) + str(rec.categ_id.code)
            rec.get_code()




    # @api.onchange('categ_id','variety_id','class_class','size','origin_id','uom_id','brand','is_great_a','is_great_b')
    # def get_name_all(self):
    #     for rec in self:
    #         rec.name=str(rec.categ_id.name)+' '+str(rec.variety_id.name)+' '+' - '+'class'+str(rec.class_class)+' - '+'size'+str(rec.size)+' - '+str(rec.origin_id.name[3]) if rec.origin_id else ''+' - '+str(rec.uom_id.name)+str(rec.brand)+' - '+'A' if rec.is_great_a else 'B'


    # @api.onchange('is_great_a','is_great_b','type_id','purchase_indicator','categ_id.code')
    # def get_identification(self):
    #     for rec in self:
    #         rec.identification = 'A' + str(rec.type_id.name[2]) + str(rec.purchase_indicator[2])+str(rec.categ_id.code) if rec.is_great_a else 'B' + str(rec.type_id.name[2]) + str(rec.purchase_indicator[2])+str(rec.categ_id.code)
    #         rec.get_code()


    @api.onchange('identification')
    def get_code(self):
        for rec in self:
            old_sequence= self.env['product.template'].sudo().search([('identification','=',rec.identification)],).mapped('sequence')
            if old_sequence :
                old_sequence = max(old_sequence) + 1
            else:
                old_sequence = 1
            if len(str(old_sequence)) <= 5:
                sequence = str(rec.identification) + '' +  (5 - len(str(old_sequence))) * '0' + str(old_sequence)
                rec.code = sequence
                rec.sequence = old_sequence




class EditProductProduct(models.Model):
    _inherit = 'product.product'

    # variety_id = fields.Many2one(comodel_name="variety", string="Variety", required=False, )
    # class_class = fields.Integer(string="Class", required=False, )
    # size = fields.Char(string="Size", required=False, )
    # origin_id = fields.Many2one(comodel_name="origin", string="Origin", required=False, )
    # net_weight = fields.Float(string="Net Weight", required=False, )
    # brand = fields.Char(string="Brand", required=False, )
    # type_id = fields.Many2one(comodel_name="type", string="Type", required=False, )
    # purchase_indicator = fields.Selection(string="Purchase Indicator", selection=[('purchasable', 'Purchasable'), (
    # 'un_purchasable', 'UnPurchasable'), ], required=False, )
    # serial_code = fields.Char(string="Serial Code", required=False, digits=(5, 2), )
    # identification = fields.Char(string="Identification", required=False, )
    # code = fields.Char(string="Code", required=False, copy=False)
    # sequence = fields.Integer(string="Sequence", required=False, default=0, copy=False)

    def button_generate_name(self):
        for rec in self:
            if rec.origin_id:
                print('ddddddddddddddddddd', str(rec.origin_id.name[0:3]))
                rec.name = str(rec.categ_id.name) + ' ' + str(rec.variety_id.name) + ' ' + ' - ' + 'class' + str(
                    rec.class_class) + ' - ' + 'size' + str(rec.size) + ' - ' + str(
                    rec.origin_id.name[0:3]) + ' - ' + str(rec.uom_id.name) + str(
                    rec.brand) + ' - ' + 'A' if rec.is_great_a else 'B'
            else:
                rec.name = str(rec.categ_id.name) + ' ' + str(rec.variety_id.name) + ' ' + ' - ' + 'class' + str(
                    rec.class_class) + ' - ' + 'size' + str(rec.size) + ' - ' + str(rec.uom_id.name) + str(
                    rec.brand) + ' - ' + 'A' if rec.is_great_a else 'B'
            if rec.is_great_a:
                rec.identification = 'A' + str(rec.type_id.name[0]) + str(rec.purchase_indicator[0]) + str(
                    rec.categ_id.code)
            elif rec.is_great_b:
                print('rec.type_id.name', rec.type_id.name)
                print(str(rec.type_id.name[0]), 'str(rec.type_id.name[0])')
                rec.identification = 'B' + str(rec.type_id.name[0]) + str(
                    rec.purchase_indicator[0]) + str(rec.categ_id.code)
            rec.get_code()

    # @api.onchange('categ_id','variety_id','class_class','size','origin_id','uom_id','brand','is_great_a','is_great_b')
    # def get_name_all(self):
    #     for rec in self:
    #         rec.name=str(rec.categ_id.name)+' '+str(rec.variety_id.name)+' '+' - '+'class'+str(rec.class_class)+' - '+'size'+str(rec.size)+' - '+str(rec.origin_id.name[3]) if rec.origin_id else ''+' - '+str(rec.uom_id.name)+str(rec.brand)+' - '+'A' if rec.is_great_a else 'B'

    # @api.onchange('is_great_a','is_great_b','type_id','purchase_indicator','categ_id.code')
    # def get_identification(self):
    #     for rec in self:
    #         rec.identification = 'A' + str(rec.type_id.name[2]) + str(rec.purchase_indicator[2])+str(rec.categ_id.code) if rec.is_great_a else 'B' + str(rec.type_id.name[2]) + str(rec.purchase_indicator[2])+str(rec.categ_id.code)
    #         rec.get_code()

    @api.onchange('identification')
    def get_code(self):
        for rec in self:
            old_sequence = self.env['product.template'].sudo().search(
                [('identification', '=', rec.identification)], ).mapped('sequence')
            if old_sequence:
                old_sequence = max(old_sequence) + 1
            else:
                old_sequence = 1
            if len(str(old_sequence)) <= 5:
                sequence = str(rec.identification) + '' + (5 - len(str(old_sequence))) * '0' + str(old_sequence)
                rec.code = sequence
                rec.sequence = old_sequence


class Variety(models.Model):
    _name = 'variety'
    _rec_name = 'name'
    _description = 'variety'

    name = fields.Char()



class Origin(models.Model):
    _name = 'origin'
    _rec_name = 'name'
    _description = 'origin'

    name = fields.Char()



class Type(models.Model):
    _name = 'type'
    _rec_name = 'name'
    _description = 'type'

    name = fields.Char()


