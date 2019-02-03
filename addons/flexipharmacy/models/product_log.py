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

from odoo import api, fields, models


class ProductIndex(models.Model):
    _name = 'product.index'

    updated = fields.Char('Updated', default='')
    created = fields.Char('Created', default='')
    deleted = fields.Char('Deleted', default='')

    @api.model
    def get_latest_version(self, old_version):
        if old_version:
            self.env.cr.execute('select id from product_index WHERE id >= %s order by id desc limit 1' % (old_version,))
        else:
            self.env.cr.execute('select id from product_index order by id desc limit 1')
        version = self.env.cr.fetchone()

        version = version[0] if version and len(version) > 0 else 0
        return version

    @api.model
    def synchronize(self, client_version):
        all_changed = self.search([('id', '>', client_version)])

        updated = ''
        created = ''
        deleted = ''

        for o in all_changed:
            updated = updated + ',' + o.updated if o.updated else updated
            created = created + ',' + o.created if o.created else created
            deleted = deleted + ',' + o.deleted if o.deleted else deleted

        update_ids = [int(x) for x in updated.split(',') if x.isdigit()]
        create_ids = [int(x) for x in created.split(',') if x.isdigit()]
        delete_ids = [int(x) for x in deleted.split(',') if x.isdigit()]

        disable_in_pos = self.env['product.product'].search([('id', 'in', update_ids), '|',
                                                             ('available_in_pos', '=', False),
                                                             ('active', '=', False)])
        disable_ids = [p.id for p in disable_in_pos]

        create_ids = list(set(update_ids + create_ids))

        return {
            'create': create_ids,
            'delete': delete_ids,
            'disable': disable_ids,
            'latest_version': self.get_latest_version(client_version),
        }


class ProductLog(models.Model):
    _inherit = 'product.product'

    @api.model
    def create(self, values):
        res = super(ProductLog, self).create(values)
        if res.ids:
            self.env['product.index'].create({'created': ','.join([str(x) for x in res.ids])})
        return res

    @api.multi
    def write(self, values):
        if self.ids:
            self.env['product.index'].create({'updated': ','.join([str(x) for x in self.ids])})
        return super(ProductLog, self).write(values)

    @api.multi
    def unlink(self):
        if self.ids:
            self.env['product.index'].create({'deleted': ','.join([str(x) for x in self.ids])})
        return super(ProductLog, self).unlink()


class ProductTemplateLog(models.Model):
    _inherit = 'product.template'

    @api.multi
    def write(self, values):
        res = super(ProductTemplateLog, self).write(values)
        for o in self:
            if o.product_variant_ids:
                self.env['product.index'].create({'updated': ','.join([str(x) for x in o.product_variant_ids.ids])})
        return res

    @api.multi
    def unlink(self):
        for o in self:
            if o.product_variant_ids:
                self.env['product.index'].create({'deleted': ','.join([str(x) for x in o.product_variant_ids.ids])})
        return super(ProductTemplateLog, self).unlink()

# class ProductAttributePriceLog(models.Model):
#     _inherit = 'product.attribute.price'
#
#     @api.model
#     def create(self, vals):
#         res = super(ProductAttributePriceLog, self).create(vals)
#         p_tmpl = res.product_tmpl_id
#         self.env['product.index'].create({'updated': ','.join([str(x) for x in p_tmpl.product_variant_ids.ids])})
#         return res
#
#     @api.multi
#     def write(self, values):
#         for o in self:
#             p_tmpl = o.product_tmpl_id
#             print(p_tmpl.product_variant_ids.ids)
#             self.env['product.index'].create({'updated': ','.join([str(x) for x in p_tmpl.product_variant_ids.ids])})
#         return super(ProductAttributePriceLog, self).write(values)
#
#     @api.multi
#     def unlink(self):
#         for o in self:
#             p_tmpl = o.product_tmpl_id
#             self.env['product.index'].create({'updated': ','.join([str(x) for x in p_tmpl.product_variant_ids.ids])})
#         return super(ProductAttributePriceLog, self).unlink()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
