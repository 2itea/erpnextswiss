# Copyright (c) 2017-2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import rounded

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Link", "options": "Item", "width": 100},
        {"label": _("Debit"), "fieldname": "debit", "fieldtype": "Currency", "width": 120},
        {"label": _("Credit"), "fieldname": "credit", "fieldtype": "Currency", "width": 120},
        {"label": _("Balance"), "fieldname": "balance", "fieldtype": "Currency", "width": 120},
        {"label": _("Against"), "fieldname": "against", "fieldtype": "Data", "width": 100},
        {"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 200},
        {"label": _("Voucher type"), "fieldname": "voucher_type", "fieldtype": "Data", "width": 100},
        {"label": _("Voucher"), "fieldname": "voucher", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 120},
        {"label": _("Tax Code"), "fieldname": "tax_code", "fieldtype": "Data", "width": 120},
        {"label": _(""), "fieldname": "blank", "fieldtype": "Data", "width": 20}
    ]

def get_data(filters):
    # fetch accounts
    account_conditions = ""
    transaction_conditions = ""
    if filters.get("from_account"):
        account_conditions += " AND `account_number` >= {0} ".format(filters.get("from_account"))
    if filters.get("to_account"):
        account_conditions += " AND `account_number` <= {0} ".format(filters.get("to_account"))
    if filters.get("cost_center"):
        transaction_conditions += """ AND `cost_center` = "{0}" """.format(filters.get("cost_center"))
        
    accounts = frappe.db.sql("""SELECT `name`
        FROM `tabAccount`
        WHERE `disabled` = 0
          AND `is_group` = 0
          AND `company` = "{company}"
          {conditions}
          ORDER BY `name` ASC;""".format(company=filters.get("company"), conditions=account_conditions), as_dict=True)
    
    data = []
    # compute each account
    for account in accounts:
        # insert account head
        data.append({'remarks': account['name']})
        # get opening balance
        opening_balance = frappe.db.sql("""SELECT 
                IFNULL(SUM(`debit`), 0) AS `debit`,
                IFNULL(SUM(`credit`), 0) AS `credit`
            FROM `tabGL Entry`
            WHERE `account` = "{account}"
              AND `docstatus` = 1
              AND DATE(`posting_date`) < "{from_date}"
              {conditions};""".format(conditions=transaction_conditions,
            account=account['name'], from_date=filters.get("from_date")), as_dict=True)[0]
        if opening_balance['debit'] > opening_balance['credit']:
            opening_debit = opening_balance['debit'] - opening_balance['credit']
            opening_credit = 0
        else:
            opening_debit = 0
            opening_credit = opening_balance['credit'] - opening_balance['debit']
        opening_balance = opening_debit - opening_credit
        data.append({
            'date': filters.get("from_date"), 
            'debit': opening_debit,
            'credit': opening_credit,
            'balance': opening_balance,
            'remarks': _("Opening")
        })
        # get positions
        positions = frappe.db.sql("""SELECT 
                `posting_date` AS `posting_date`,
                `debit` AS `debit`,
                `credit` AS `credit`,
                `remarks` AS `remarks`,
                `voucher_type` AS `voucher_type`,
                `voucher_no` AS `voucher`,
                `against` AS `against`
            FROM `tabGL Entry`
            WHERE `account` = "{account}"
              AND `docstatus` = 1
              AND DATE(`posting_date`) >= "{from_date}"
              AND DATE(`posting_date`) <= "{to_date}"
              {conditions}
            ORDER BY `posting_date` ASC;""".format(conditions=transaction_conditions,
            account=account['name'], from_date=filters.get("from_date"), to_date=filters.get("to_date")), as_dict=True)
        for position in positions:
            opening_debit += position['debit']
            opening_credit += position['credit']
            opening_balance = opening_balance - position['credit'] + position['debit']
            if "," in (position['against'] or ""):
                against = "{0} (...)".format((position['against'] or "").split(" ")[0])
            else:
                against = (position['against'] or "").split(" ")[0]
            if len(position['remarks'] or "") > 30:
                remarks = "{0}...".format(position['remarks'][:30])
            else:
                remarks = position['remarks']
            # extend tax code
            tax_code = None
            if position['voucher_type'] in ["Sales Invoice", "Purchase Invoice"]:
                tax_code = frappe.get_value(position['voucher_type'], position['voucher'], "taxes_and_charges")
            data.append({
                'date': position['posting_date'], 
                'debit': position['debit'],
                'credit': position['credit'],
                'balance': opening_balance,
                'voucher_type': position['voucher_type'],
                'voucher': position['voucher'],
                'against': against,
                'remarks': remarks,
                'tax_code': tax_code
            })
        # add closing balance
        data.append({
            'date': filters.get("to_date"), 
            'debit': opening_debit,
            'credit': opening_credit,
            'balance': opening_balance,
            'remarks': _("Closing")
        })

    return data


@frappe.whitelist()
def get_csv(company, from_date, to_date, from_account=None, to_account=None, cost_center=None):
    filters = {
        'company': company, 
        'from_date': from_date, 
        'to_date': to_date, 
        'from_account': from_account if from_account else None, 
        'to_account': to_account if to_account else None,
        'cost_center': cost_center if cost_center else None
    }

    columns = get_columns(filters)
    data = get_data(filters)

    output = ""
    # add headers
    for c in columns:
        output += ("{0};".format(c.get('label')))
    output += "\r\n"

    # add each row
    for d in data:
        for c in columns:
            if c.get("fieldtype") == "Currency":
                value = "{0:.2f};".format(rounded(d.get(c.get('fieldname')) or 0, 2))
            else:
                value = ("{0};".format(d.get(c.get('fieldname')) or "")).replace("\r", " ").replace("\n", " ")
            output += value
        output += "\r\n"
        
    # return download
    frappe.local.response.filename = "account_sheets_{0}_{1}.csv".format(from_date, to_date)
    frappe.local.response.filecontent = output
    frappe.local.response.type = "download"
