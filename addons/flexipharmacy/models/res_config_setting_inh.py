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
import ast

from odoo import models, fields, api, _


class ResSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mailsend_check = fields.Boolean(string="Send Mail")
    email_notification_days = fields.Integer(string="Expiry Alert Days")
    res_user_ids = fields.Many2many('res.users', string='Users')

    @api.model
    def get_values(self):
        res = super(ResSettings, self).get_values()
        param_obj = self.env['ir.config_parameter']
        res_user_ids = param_obj.sudo().get_param('aspl_product_expiry_alert.res_user_ids')
        if res_user_ids:
            res.update({'res_user_ids': ast.literal_eval(res_user_ids)})

        res.update(
            mailsend_check=self.env['ir.config_parameter'].sudo().get_param('aspl_product_expiry_alert.mailsend_check'),
            email_notification_days=int(param_obj.sudo().get_param('aspl_product_expiry_alert.email_notification_days'))
        )
        return res

    @api.multi
    def set_values(self):
        super(ResSettings, self).set_values()
        param_obj = self.env['ir.config_parameter']
        param_obj.sudo().set_param('aspl_product_expiry_alert.mailsend_check', self.mailsend_check)
        param_obj.sudo().set_param('aspl_product_expiry_alert.res_user_ids', self.res_user_ids.ids)
        param_obj.sudo().set_param('aspl_product_expiry_alert.email_notification_days', self.email_notification_days)
