# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CustomerIndex(models.Model):
    _name = 'customer.index'

    updated = fields.Char('Updated', default='')
    created = fields.Char('Created', default='')
    deleted = fields.Char('Deleted', default='')

    @api.model
    def get_latest_version(self, old_version):
        if old_version:
            self.env.cr.execute(
                'select id from customer_index WHERE id >= %s order by id desc limit 1' % (old_version,))
        else:
            self.env.cr.execute('select id from customer_index order by id desc limit 1')
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

        disable_in_pos = self.env['res.partner'].search([('id', 'in', update_ids), '|',
                                                         ('customer', '=', False),
                                                         ('active', '=', False)])
        disable_ids = [p.id for p in disable_in_pos]

        create_ids = list(set(update_ids + create_ids))

        return {
            'create': create_ids,
            'delete': delete_ids,
            'disable': disable_ids,
            'latest_version': self.get_latest_version(client_version),
        }


class CustomerLog(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, values):
        res = super(CustomerLog, self).create(values)
        if res.ids and res.customer:
            self.env['customer.index'].create({'created': ','.join([str(x) for x in res.ids])})
        return res

    @api.multi
    def write(self, values):
        if self.ids:
            customers = self.filtered(lambda record: record.customer)
            if len(customers) > 0:
                self.env['customer.index'].create({'updated': ','.join([str(x) for x in customers.ids])})
        return super(CustomerLog, self).write(values)

    @api.multi
    def unlink(self):
        if self.ids:
            customers = self.filtered(lambda record: record.customer)
            if len(customers) > 0:
                self.env['customer.index'].create({'deleted': ','.join([str(x) for x in customers.ids])})
        return super(CustomerLog, self).unlink()
