# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
# You should have received a copy of the License along with this program.
#################################################################################

from odoo import models, fields, api, _
import time, datetime
from datetime import datetime
from dateutil.relativedelta import relativedelta


class POSRecurrentOrder(models.Model):
    _name = 'pos.recurrent.order'
    _rec_name = 'partner_id'
    _description = 'Pos recurrent'

    partner_id = fields.Many2one('res.partner', string="Customer", required='1')
    pos_config_id = fields.Many2one('pos.config', string="Point of Sale", required='1')
    pos_user_id = fields.Many2one('res.users', string="POS User", required='1')
    product_line = fields.One2many('pos.recurrent.prod.line', 'recurrent_id', string="Products")
    active = fields.Boolean('Active', default=True)
    is_deliver = fields.Boolean('Is Deliver')
    deli_address = fields.Text('Delivery Address')
    no_of_day = fields.Integer('Number of days', required='1')
    next_exe_date = fields.Date(string="Next Execution Date", required='1')

    @api.onchange('partner_id')
    def on_change_partner_id(self):
        if self.partner_id:
            self.deli_address = ''
            if self.partner_id.street:
                self.deli_address += self.partner_id.street
            if self.partner_id.street2:
                self.deli_address += ' ' + self.partner_id.street2
            if self.partner_id.city:
                self.deli_address += ' ' + self.partner_id.city
            if self.partner_id.state_id:
                self.deli_address += ' ' + self.partner_id.state_id.name
            if self.partner_id.zip:
                self.deli_address += ' ' + self.partner_id.zip
            if self.partner_id.country_id:
                self.deli_address += ' ' + self.partner_id.country_id.name

    @api.onchange('no_of_day')
    def on_change_no_of_day(self):
        next_dt2 = datetime.now() + relativedelta(days=self.no_of_day)
        if next_dt2 and next_dt2.date():
            self.next_exe_date = next_dt2.date()

    @api.model
    def recurrent_order_cron(self):
        for each in self.search([]):
            if each.next_exe_date == datetime.now().date():
                order_lines = []
                amount_tax = []
                if each.is_deliver:
                    rec_order_delivery = True
                else:
                    rec_order_delivery = False
                for line in each.product_line:
                    prod_id = line.product_id.id
                    qty = line.qty
                    price = line.unit_price
                    product_data = self.env['product.product'].browse(prod_id)
                    total_tax_amount = 0.00
                    tax_ids = []
                    if product_data and product_data.taxes_id:
                        for each_tax in product_data.taxes_id:
                            tax_res = each_tax.compute_all(price, None, qty, prod_id, each.partner_id)
                            total_tax_amount += tax_res['taxes'][0]['amount']
                            tax_ids.append(each_tax.id)

                    amount_tax.append(total_tax_amount)
                    total_price = price * qty
                    line = (0, 0, {
                        'qty': qty,
                        'product_id': prod_id,
                        'price_unit': price,
                        'price_subtotal': total_price,
                        'tax_ids': [[6, False, tax_ids]],
                        'price_subtotal_incl': total_price + total_tax_amount,
                    })
                    order_lines.append(line)

                order_amount_total = 0.00
                for each_order_line in order_lines:
                    order_amount_total += each_order_line[2]['price_subtotal_incl']

                tax_amount = 0.00
                for tax in amount_tax:
                    tax_amount += tax;
                self.env['pos.order'].create({
                    'name': 'Shop/0001',
                    'partner_id': each.partner_id.id,
                    'lines': order_lines,
                    'session_id': 1,
                    'is_recurrent': True,
                    'is_delivery_recurrent': rec_order_delivery,
                    'user_id': each.pos_user_id.id,
                    'amount_tax': tax_amount,
                    'amount_total': order_amount_total,
                    'amount_paid': 0,
                    'amount_return': 0,
                    'pricelist_id': 1,
                    'fiscal_position_id': False
                })


class PosRecurrentProdLine(models.Model):
    _name = 'pos.recurrent.prod.line'
    _rec_name = 'product_id'
    _description = 'Pos recurrent Line'

    recurrent_id = fields.Many2one('pos.recurrent.order', string="Card", readonly=True)
    product_id = fields.Many2one('product.product', string="Product")
    qty = fields.Integer(string="Quantity", default=1)
    unit_price = fields.Float(string="Unit Price")

    @api.onchange('product_id')
    def on_change_product_id(self):
        if self.product_id:
            self.unit_price = self.product_id.lst_price

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
