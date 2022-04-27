# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_cancel(self):
        self = self.with_context(disable_cancel_warning=True)
        res = super(SaleOrder, self).action_cancel()
        for picking_id in self.picking_ids:
            if picking_id.state == 'done':
                register_picking = self.env[
                    'stock.return.picking'].with_context({
                        'active_model': picking_id._name,
                        'active_id': picking_id.id
                    }).create({
                        'picking_id': picking_id.id
                    })
                register_picking._onchange_picking_id()

                for return_line_rec in register_picking.product_return_moves:
                    # if return_line_rec.quantity
                    stock_move_line_rec = self.env['stock.move.line'].search([
                        ('picking_id', '=', picking_id.id),
                        ('product_id', '=', picking_id.product_id.id),
                        ('location_id', '=', picking_id.location_id.id)],
                        limit=1)
                    if stock_move_line_rec and return_line_rec.quantity !=\
                            stock_move_line_rec.qty_done:
                        return_line_rec.write(
                            {'quantity': stock_move_line_rec.qty_done})
                return_rec = register_picking.create_returns()
                if return_rec.get('res_model', '') and\
                        return_rec.get('res_id'):
                    return_id = self.env[
                        return_rec.get('res_model', '')].browse(
                            return_rec.get('res_id'))
                    for line in return_id.move_ids_without_package:
                        line.write({'quantity_done': line.product_uom_qty})
                    return_id.button_validate()
        for invoice_rec in self.invoice_ids:
            if invoice_rec.state not in ['draft', 'cancel']:
                move_reversal = self.env[
                    'account.move.reversal'].with_context(
                        active_model=invoice_rec._name,
                        active_ids=invoice_rec.ids).create({
                            'date': fields.Date.today(),
                            'reason': 'cancel sale order',
                            'refund_method': 'cancel',
                        })
                move_reversal.reverse_moves()
        return res
