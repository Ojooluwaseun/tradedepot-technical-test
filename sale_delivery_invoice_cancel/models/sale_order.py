# Copyright 2022-TODAY Anand Kansagra <kansagra.anand27@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_cancel_picking(self):
        """Automatically cancels the picking when SO is cancelled."""
        for rec in self:
            for picking_id in rec.picking_ids.filtered(
                    lambda x: x.state == 'done'):
                stock_return_picking_id = self.env[
                    'stock.return.picking'].with_context({
                        'active_model': picking_id._name,
                        'active_id': picking_id.id
                    }).create({
                        'picking_id': picking_id.id
                    })
                stock_return_picking_id._onchange_picking_id()
                for product_return_moves_id in\
                        stock_return_picking_id.product_return_moves:
                    stock_move_line_rec = self.env[
                        'stock.move.line'].search([
                            ('picking_id', '=', picking_id.id),
                            ('product_id', '=', picking_id.product_id.id),
                            ('location_id', '=',
                                picking_id.location_id.id)],
                        limit=1)
                    if stock_move_line_rec and\
                        product_return_moves_id.quantity !=\
                            stock_move_line_rec.qty_done:
                        product_return_moves_id.write(
                            {'quantity': stock_move_line_rec.qty_done})
                return_picking_data = stock_return_picking_id.create_returns()
                if return_picking_data.get('res_model', '') and\
                        return_picking_data.get('res_id'):
                    return_id = self.env[
                        return_picking_data.get('res_model', '')].browse(
                            return_picking_data.get('res_id'))
                    for line in return_id.move_ids_without_package:
                        line.write({'quantity_done': line.product_uom_qty})
                    return_id.button_validate()

    def action_cancel_invoice(self):
        """Automatically cancels the invoice when SO is cancelled."""
        for rec in self:
            for invoice_id in rec.invoice_ids.filtered(
                    lambda x: x.state not in ('draft', 'cancel')):
                account_move_reversal_id = self.env[
                    'account.move.reversal'].with_context(
                        active_model=invoice_id._name,
                        active_ids=invoice_id.ids).create({
                            'date': fields.Date.today(),
                            'reason': 'Sale Order' + rec.name + 'Cancelled',
                            'refund_method': 'cancel',
                        })
                account_move_reversal_id.reverse_moves()

    def action_cancel(self):
        """Call the cancel delivery order and invoice method."""
        self = self.with_context(disable_cancel_warning=True)
        self.action_cancel_picking()
        self.action_cancel_invoice()
        return super(SaleOrder, self).action_cancel()
