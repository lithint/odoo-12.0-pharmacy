# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ChangeDetector(models.TransientModel):
    _name = 'change_detector'

    def broadcast(self, message):
        self.env['bus.bus'].sendone((self._cr.dbname, 'change_detector'), message)


class Product(models.Model):
    _inherit = 'product.index'

    @api.model
    def create(self, vals):
        res = super(Product, self).create(vals)
        self.env['change_detector'].broadcast({'p': res.id})
        return res

    @api.model
    def sync_not_reload(self, client_version=0, _fields=None):
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

        create_set = set(update_ids + create_ids)
        delete_set = set(delete_ids + disable_ids)

        _fields = [] if not _fields else _fields
        records = self.env['product.product'].with_context(display_default_code=False) \
            .search_read([('id', 'in', list(create_set - delete_set))], _fields)

        return {
            'create': records,
            'delete': list(delete_set),
            'latest_version': self.get_latest_version(client_version),
        }


class Customer(models.Model):
    _inherit = 'customer.index'

    @api.model
    def create(self, vals):
        res = super(Customer, self).create(vals)
        self.env['change_detector'].broadcast({'c': res.id})
        return res

    @api.model
    def sync_not_reload(self, client_version=0, _fields=None):
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

        disable_in_pos = self.env['res.partner'].search([('id', 'in', update_ids), '|',
                                                         ('customer', '=', False),
                                                         ('active', '=', False)])
        disable_ids = [p.id for p in disable_in_pos]

        create_set = set(update_ids + create_ids)
        delete_set = set(delete_ids + disable_ids)

        _fields = [] if not _fields else _fields
        records = self.env['res.partner'].search_read([('id', 'in', list(create_set - delete_set))], _fields)

        return {
            'create': records,
            'delete': list(delete_set),
            'latest_version': self.get_latest_version(client_version),
        }
