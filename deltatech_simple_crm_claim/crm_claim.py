# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import openerp
from openerp import models, fields, api, _
from openerp.tools import html2plaintext


class crm_case_categ(models.Model):
    """ Category of Case """
    _name = "crm.case.categ"
    _description = "Category of Case"

    @api.model
    def _find_object_id(self):
        """Finds id for case object"""
        object_id = self.env.context.get('object_id', False)
        object_name = self.env.context.get('object_name', False)
        object_id = self.env['ir.model'].search(['|', ('id', '=', object_id), ('model', '=', object_name)], limit=1)
        return object_id

    name = fields.Char('Name', required=True, translate=True)
    section_id = fields.Many2one('crm.case.section', 'Sales Team')
    object_id = fields.Many2one('ir.model', 'Object Name', default=_find_object_id)


class crm_claim_stage(models.Model):
    """ Model for claim stages. This models the main stages of a claim
        management flow. Main CRM objects (leads, opportunities, project
        issues, ...) will now use only stages, instead of state and stages.
        Stages are for example used to display the kanban view of records.
    """
    _name = "crm.claim.stage"
    _description = "Claim stages"
    _rec_name = 'name'
    _order = "sequence"

    name = fields.Char('Stage Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', help="Used to order stages. Lower is better.", default=1)
    section_ids = fields.Many2many('crm.case.section', 'section_claim_stage_rel', 'stage_id', 'section_id',
                                   string='Sections',
                                   help="Link between stages and sales teams. When set, this limitate the current stage to the selected sales teams.")
    case_default = fields.Boolean('Common to All Teams',
                                  help="If you check this field, this stage will be proposed by default on each sales team. It will not assign this stage to existing teams.")


class crm_claim(models.Model):
    """ Crm claim
    """
    _name = "crm.claim"
    _description = "Claim"
    _order = "priority,date desc"
    _inherit = ['mail.thread']

    @api.model
    def _resolve_section_id_from_context(self):
        """ Returns ID of section based on the value of 'section_id'
            context key, or None if it cannot be resolved to a single
            Sales Team.
        """

        if type(self.env.context.get('default_section_id')) in (int, long):
            return self.env.context.get('default_section_id')
        if isinstance(self.env.context.get('default_section_id'), basestring):
            section_ids = self.env['crm.case.section'].name_search(name=self.env.context['default_section_id'])
            if len(section_ids) == 1:
                return int(section_ids[0][0])
        return None

    @api.model
    def _get_default_section_id(self):
        return self._resolve_section_id_from_context() or False

    @api.model
    def _get_default_stage_id(self):
        section_id = self._get_default_section_id()
        return self.stage_find(section_id, [('sequence', '=', '1')])

    @api.model
    def _reference_models(self):
        models = self.env['res.request.link'].search([])
        return [(model.object, model.name) for model in models]



    id = fields.Integer('ID', readonly=True)
    name = fields.Char('Claim Subject', required=True)
    active = fields.Boolean('Active', default=1)
    action_next = fields.Char('Next Action')
    date_action_next = fields.Datetime('Next Action Date')
    description = fields.Text('Description')
    resolution = fields.Text('Resolution')
    create_date = fields.Datetime('Creation Date', readonly=True)
    write_date = fields.Datetime('Update Date', readonly=True)
    date_deadline = fields.Date('Deadline')
    date_closed = fields.Datetime('Closed', readonly=True)
    date = fields.Datetime('Claim Date', select=True, defalut=fields.Datetime.now)

    #ref = fields.Char()
    ref = fields.Reference(string='Reference',selection = '_reference_models' )
    #ref = fields.Reference(string='Reference', selection=openerp.addons.base.res.res_request.referencable_models)

    categ_id = fields.Many2one('crm.case.categ', 'Category',
                               domain="[('section_id','=',section_id),   ('object_id.model', '=', 'crm.claim')]")
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], 'Priority', default=1)
    type_action = fields.Selection([('correction', 'Corrective Action'), ('prevention', 'Preventive Action')],
                                   'Action Type')
    user_id = fields.Many2one('res.users', 'Responsible', track_visibility='always', default=lambda self: self.env.use)
    user_fault = fields.Char('Trouble Responsible')
    section_id = fields.Many2one('crm.case.section', 'Sales Team', default=_get_default_section_id,
                                 select=True, help="Responsible sales team." \
                                                   " Define Responsible user and Email account for" \
                                                   " mail gateway.")
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env['res.company']._company_default_get('crm.case'))
    partner_id = fields.Many2one('res.partner', 'Partner')
    email_cc = fields.Text('Watchers Emails', size=252,
                           help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma")
    email_from = fields.Char('Email', size=128, help="Destination email for email gateway.")
    partner_phone = fields.Char('Phone')
    stage_id = fields.Many2one('crm.claim.stage', 'Stage', track_visibility='onchange', default=_get_default_stage_id,
                               domain="['|', ('section_ids', '=', section_id), ('case_default', '=', True)]")
    cause = fields.Text('Root Cause')

    @api.model
    def stage_find(self, cases, section_id, domain=[], order='sequence'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - section_id: if set, stages must belong to this section or
              be a default case
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cases)
        # collect all section_ids
        section_ids = []
        if section_id:
            section_ids.append(section_id)
        for claim in cases:
            if claim.section_id:
                section_ids.append(claim.section_id.id)
        # OR all section_ids and OR with case_default
        search_domain = []
        if section_ids:
            search_domain += [('|')] * len(section_ids)
            for section_id in section_ids:
                search_domain.append(('section_ids', '=', section_id))
        search_domain.append(('case_default', '=', True))
        # AND with the domain in parameter
        search_domain += list(domain)
        # perform search, return the first found
        stage_ids = self.env['crm.claim.stage'].search(search_domain, order=order)
        if stage_ids:
            return stage_ids[0]
        return False

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            return {'value': {'email_from': False, 'partner_phone': False}}
        address = self.partner_id
        return {'value': {'email_from': address.email, 'partner_phone': address.phone}}

    @api.model
    def create(self, vals):
        if vals.get('section_id') and not self.env.context.get('default_section_id'):
            default_section_id = vals.get('section_id')
            self = self.with_context(default_section_id=default_section_id)

        # context: no_log, because subtype already handle this
        return super(crm_claim, self).create(vals)


    @api.multi
    def copy(self, default=None):
        claim = self
        default = dict(default or {},  stage_id=self._get_default_stage_id(), name=_('%s (copy)') % claim.name)
        return super(crm_claim, self).copy(default)

    # -------------------------------------------------------
    # Mail gateway
    # -------------------------------------------------------

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        desc = html2plaintext(msg_dict.get('body')) if msg_dict.get('body') else ''
        defaults = {
            'name': msg_dict.get('subject') or _("No Subject"),
            'description': desc,
            'email_from': msg_dict.get('from'),
            'email_cc': msg_dict.get('cc'),
            'partner_id': msg_dict.get('author_id', False),
        }
        if msg_dict.get('priority'):
            defaults['priority'] = msg_dict.get('priority')
        defaults.update(custom_values)
        return super(crm_claim, self).message_new( msg_dict, custom_values=defaults)




class res_partner(models.Model):
    _inherit = 'res.partner'

    claim_count = fields.Integer(string='# Claims', compute='_compute_claim_count')

    @api.multi
    def _compute_claim_count(self):
        for partner in self:
            partner.claim_count = self.env['crm.claim'].search_count([('partner_id', '=', partner.id)])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
