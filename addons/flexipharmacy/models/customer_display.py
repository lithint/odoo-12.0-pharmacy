# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import models, fields, api, _


class customer_display(models.Model):
    _name = 'customer.display'
    _description = 'Store Data Which Used to Display in Customer Screen.'

    @api.model
    def load_config(self, config_id):
        if config_id:
            config_obj = self.env['pos.config'].search_read([('id', '=', config_id)],
                                                            ['customer_display', 'image_interval',
                                                             'customer_display_details_ids', 'enable_customer_rating',
                                                             'set_customer'])
            if config_obj:
                return config_obj
        return False

    @api.model
    def search_create_customer(self, name, email, mobile, config_id):
        if mobile:
            partner = self.env['res.partner'].search([('mobile', 'ilike', mobile)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'company_type': 'person',
                    'name': name,
                    'email': email,
                    'mobile': mobile,
                })
            if partner:
                notifications = []
                session_obj = self.env['pos.session'].search([('config_id', '=', config_id), ('state', '=', 'opened')],
                                                             limit=1)
                partner_id = partner.id
                if session_obj:
                    notifications.append(
                        [(self._cr.dbname, 'lock.data', session_obj.user_id.id), {'partner_id': partner_id}])
                    self.env['bus.bus'].sendmany(notifications)
        return True

    @api.model
    def search_customer(self, mobile, config_id):
        if mobile:
            partner = self.env['res.partner'].search([('mobile', 'ilike', mobile)], limit=1)
            if partner:
                notifications = []
                session_obj = self.env['pos.session'].search([('config_id', '=', config_id), ('state', '=', 'opened')],
                                                             limit=1)
                if session_obj:
                    notifications.append(
                        [(self._cr.dbname, 'lock.data', session_obj.user_id.id), {'partner_id': partner.id}])
                    self.env['bus.bus'].sendmany(notifications)
                return True
        return False

    @api.model
    def load_customer_display_data(self, config_id):
        if config_id:
            config_obj = self.env['pos.config'].browse(config_id);
            if config_obj and config_obj.customer_display_details_ids:
                cust_disp_ids = config_obj.customer_display_details_ids
                if cust_disp_ids:
                    return self.search_read([('id', 'in', cust_disp_ids.ids)]) or False

    @api.model
    def load_currency(self, company_id):
        if company_id:
            company_obj = self.env['res.company'].browse(company_id)
            if company_obj and company_obj.currency_id:
                return company_obj.currency_id.read()

    @api.model
    def broadcast_data(self, data):
        notifications = []
        vals = {
            'user_id': self._uid,
            'cart_data': data.get('cart_data'),
            'customer_name': data.get('client_name'),
            'order_total': data.get('order_total'),
            'change_amount': data.get('change_amount'),
            'payment_info': data.get('payment_info'),
            'enable_customer_rating': data.get('enable_customer_rating'),
            'set_customer': data.get('set_customer'),
        }
        if data.get('new_order'):
            vals['new_order'] = True
        notifications.append([(self._cr.dbname, 'customer.display', self._uid), {'customer_display_data': vals}])
        self.env['bus.bus'].sendmany(notifications)
        return True

    @api.model
    def send_rating(self, config_id, rating_val):
        notifications = []
        session_obj = self.env['pos.session'].search([('config_id', '=', config_id), ('state', '=', 'opened')], limit=1)
        if session_obj:
            notifications.append([(self._cr.dbname, 'lock.data', session_obj.user_id.id), {'rating': rating_val}])
            self.env['bus.bus'].sendmany(notifications)
        return True

    name = fields.Char("Name")
    image = fields.Binary("Image")
    config_id = fields.Many2one('pos.config', "POS config")
