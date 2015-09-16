# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008 Deltatech All Rights Reserved
#                    Dorin Hongu <dhongu(@)gmail(.)com       
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



from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools import float_compare
import openerp.addons.decimal_precision as dp


class service_billing(models.TransientModel):
    _name = 'service.billing'
    _description = "Service Billing"
    
    journal_id = fields.Many2one('account.journal', 'Journal', required=True)
 
    
    # facturile pot fi facute grupat dupa partner sau dupa contract
    group_invoice = fields.Selection([('partner','Group by partner'),
                                      ('agreement','Group by agreement')], string="Group invoice", default='agreement')
    
    
    # indica daca liniile din facura sunt insumate dupa servicu
    
    group_service = fields.Boolean(string="Group by service",default=False)
    
    consumption_ids = fields.Many2many('service.consumption', 'service_billing_consumption', 'billing_id','consumption_id', 
                                        string='Consumptions', domain=[('invoice_id', '=', False)])
        
    @api.model
    def default_get(self, fields):
        defaults = super(service_billing, self).default_get(fields)
      
        
        active_ids = self.env.context.get('active_ids', False)
        print active_ids
        if active_ids:
            domain=[('state','=','draft'),('id','in', active_ids )]   
        else:
            domain=[('state','=','draft')]
        
        
        res = self.env['service.consumption'].search(domain)
        defaults['consumption_ids'] = [ (6,0,[rec.id for rec in res]) ]
        return defaults
        

    @api.multi
    def do_billing(self):
        pre_invoice = {}   # lista de facuri
        for cons in self.consumption_ids:
            pre_invoice[cons.date_invoice] = {}
        for cons in self.consumption_ids:
            # convertire pret in moneda companeie
            
            currency = cons.currency_id.with_context(date=cons.date_invoice or fields.Date.context_today(self)) 
             
            price_unit = currency.compute(cons.price_unit, self.env.user.company_id.currency_id )
            
            name =  cons.product_id.name

            if cons.name:
                if cons.agreement_id.invoice_mode == 'detail' or  self.group_service == False:
                    name += cons.name
            
                

            if self.group_invoice == 'agreement' or cons.agreement_id.invoice_mode == 'detail':
                key = cons.agreement_id.id
            else:
                key = cons.partner_id.id
                 
            if cons.quantity > cons.agreement_line_id.quantity_free or cons.quantity < 0 :
                invoice_line = {
                    'product_id': cons.product_id.id,
                    'quantity': cons.quantity - cons.agreement_line_id.quantity_free,
                    'price_unit': price_unit ,
                    'uos_id': cons.agreement_line_id.uom_id.id,
                    'name': name,
                    'account_id': cons.product_id.property_account_income.id or cons.product_id.categ_id.property_account_income_categ.id,
                    'invoice_line_tax_id'  : [(6, 0, (  [rec.id for rec in cons.product_id.taxes_id] ))],
                    'agreement_line_id':cons.agreement_line_id.id,
                }
                
                #este pt situatia in care se doreste stornarea unei pozitii
                if cons.quantity < 0:
                    invoice_line['quantity'] = cons.quantity
                
                if pre_invoice[cons.date_invoice].get(key,False):
                    is_prod = False
                    if ( self.group_service and  cons.agreement_id.invoice_mode!='detail' ) or cons.agreement_id.invoice_mode=='service':
                        for line in pre_invoice[cons.date_invoice][key]['lines']:
                            if line['product_id'] ==  cons.product_id.id and  float_compare(line['price_unit'],invoice_line['price_unit'], precision_digits=2) == 0 :
                                line['quantity'] += invoice_line['quantity']
                                is_prod = True
                                break
                    if not is_prod:   
                        pre_invoice[cons.date_invoice][key]['lines'].append(invoice_line)
                    pre_invoice[cons.date_invoice][key]['cons'] += cons
                    pre_invoice[cons.date_invoice][key]['agreement_ids'] |= cons.agreement_id
                else:
                    pre_invoice[cons.date_invoice][key] = {   'lines':[invoice_line],
                                           'cons':cons,
                                           'partner_id':cons.partner_id.id,
                                           'account_id':cons.partner_id.property_account_receivable.id, }
                    
                    pre_invoice[cons.date_invoice][key]['agreement_ids'] = cons.agreement_id
                cons.write({'state':'done',
                            'invoiced_qty': cons.quantity - cons.agreement_line_id.quantity_free,})  
            else: # cons.quantity < cons.agreement_line_id.quantity_free:
                cons.write({'state':'none'})   
                 
        for cons in self.consumption_ids:
            if cons.state == 'none':
                if self.group_invoice == 'agreement' or cons.agreement_id.invoice_mode == 'detail':
                    key = cons.agreement_id.id
                else:
                    key = cons.partner_id.id
                if pre_invoice[cons.date_invoice].get(key,False):  # daca a fost generata o factura atunci leg si consumul de facura pentru a aparea in centralizator
                    pre_invoice[cons.date_invoice][key]['cons'] += cons
            
                
        if not pre_invoice:
            raise Warning (_('No condition for create a new invoice') )
        res = []
        for date_invoice in pre_invoice:
            for key in pre_invoice[date_invoice]:
                comment = _('According to agreement ')
                for  agreement in pre_invoice[date_invoice][key]['agreement_ids']:
                    comment += _('%s from %s \n') % (agreement.name or '____', agreement.date_agreement or '____')
                
                
                invoice_value = { 
                    #'name': _('Invoice'),
                    'partner_id': pre_invoice[date_invoice][key]['partner_id'],
                    'journal_id': self.journal_id.id,
                    'date_invoice':date_invoice,
                    'account_id': pre_invoice[date_invoice][key]['account_id'], 
                    'type': 'out_invoice',
                    'state': 'draft',
                    'invoice_line': [(0, 0, x) for x in pre_invoice[date_invoice][key]['lines']],
                    'comment':comment,
                    #'agreement_id':pre_invoice[key]['agreement_id'],
                }
                invoice_id = self.env['account.invoice'].create(invoice_value)
                invoice_id.button_compute(True)
                pre_invoice[date_invoice][key]['cons'].write( {'invoice_id':invoice_id.id})
                res.append(invoice_id.id)

        action = self.env.ref('deltatech_service.action_service_invoice').read()[0]  
        action['domain'] = "[('id','in', ["+','.join(map(str,res))+"])]"
        return action
 

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: 