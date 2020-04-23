# -*- coding: utf-8 -*-
# Copyright (c) 2018-2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
#
#
#
import frappe, os
from frappe.utils.pdf import get_pdf
from erpnextswiss.erpnextswiss.zugferd.zugferd_xml import create_zugferd_xml
#from facturx import generate_facturx_from_binary, get_facturx_xml_from_pdf, check_facturx_xsd, generate_facturx_from_file
from erpnextswiss.erpnextswiss.zugferd.facturx.facturx.facturx import generate_facturx_from_binary
from bs4 import BeautifulSoup
from frappe.utils.file_manager import save_file
from pathlib import Path
import unicodedata
from PyPDF2 import PdfFileWriter
import xml.etree.ElementTree as ET
import xml.etree.ElementTree
from xml.etree import ElementTree
from lxml import etree

"""
Creates an XML file from a sales invoice

:params:sales_invoice:   document name of the sale invoice
:returns:                xml content (string)
"""
def create_zugferd_pdf(sales_invoice_name, verify=True, format=None, doc=None, no_letterhead=0):
    try:
        frappe.msgprint("andere1")
        doctype1 = "Sales Invoice"
        html = frappe.get_print(doctype1, sales_invoice_name, format, doc=doc, no_letterhead=no_letterhead)
        
        pdf = get_pdf(html)
        xml1 = create_zugferd_xml(sales_invoice_name)
        
       
        #facturx_pdf = generate_facturx_from_file(file, xml)  
        ## The second argument of the method generate_facturx must be either a string, an etree.Element() object or a file (it is a <class 'bytes'>).
        facturx_pdf = generate_facturx_from_binary(pdf, xml1.encode('utf-8'))  ## Unicode strings with encoding declaration are not supported. Please use bytes input or XML fragments without declaration.
        
        reca = "gut"
        print("succes")
        return facturx_pdf
    except Exception as err:
        frappe.log_error("Unable to create zugferdPDF: {0}\n{1}".format(err, xml), "ZUGFeRD")
        print("error")
        # fallback to normal pdf
        pdf = get_pdf(html)
        reca2 = "FALSCHH"
        return pdf

@frappe.whitelist()
def download_zugferd_pdf(sales_invoice_name, format=None, doc=None, no_letterhead=0, verify=True):
    frappe.msgprint("white1")
    print("test")
    frappe.local.response.filename = "{name}.pdf".format(name=sales_invoice_name.replace(" ", "-").replace("/", "-"))

    frappe.local.response.filecontent = create_zugferd_pdf(sales_invoice_name, verify, format, doc, no_letterhead)
    #html = frappe.get_print(doctype, sales_invoice_name, format, doc=doc, no_letterhead=no_letterhead)
    #frappe.local.response.filecontent = get_pdf(html)
    frappe.msgprint("white2")
    frappe.local.response.type = "download"
    return 
    
    
@frappe.whitelist()
def test(sales_invoice_name, format=None, doc=None, no_letterhead=0, verify=True):
	
    doctype = "Sales Invoice"
    html = frappe.get_print(doctype, sales_invoice_name, format, doc=doc, no_letterhead=no_letterhead)

    #pdf = get_pdf(html)
    xml = create_zugferd_xml(sales_invoice_name)
    check_facturx_xsd(facturx_xml=xml.encode('utf-8'))
    #facturx_pdf = generate_facturx_from_binary(pdf, xml.encode('utf-8')) 
    #xml_test = create_zugferd_xml(sales_invoice_name)
    return xml
    
    
    
    
    
    
    
    
@frappe.whitelist()
def test4(sales_invoice_name, format=None, doc=None, no_letterhead=0, verify=True):
    doctype = "Sales Invoice"
    html = frappe.get_print(doctype, sales_invoice_name, format, doc=doc, no_letterhead=no_letterhead)
    print("succes1")
    pdf = get_pdf(html)
    #pdf_string = pdf.decode('utf-8')
    print(pdf)
    #pdf_a = pdf.decode('ASCII')
    #pdf_c = pdf.decode('unicode_escape')
    #print(pdf_c)
    pdf_u = pdf.decode('Latin-1')
    pdf_utf = pdf_u.encode('utf-8')
    pd = pdf_utf.decode('utf-8')
    #print(pd)
    #pdf_o = pdf.decode('cp1252').encode('utf-8')
    #print(pdf_o)
    #stri = decode(pdf, errors='ignore')
    #stri = pdf.decode('cp1252').encode('utf-8')
    return pdf_u

    
    
    

#this is the method that does not work
@frappe.whitelist()    
def get_xml(file_path, doc_name):
    physical_path = "{bench_path}/sites/{site_name}{file_path}".format(
        bench_path=frappe.utils.get_bench_path(), 
        site_name=frappe.utils.get_site_path().replace("./", ""),
        file_path=file_path)
    frappe.msgprint(physical_path);
    frappe.msgprint(doc_name);
    try:
        f = open(physical_path, "rb")
        xml_name, xml_content = get_facturx_xml_from_pdf(f)
        #print(xml_content.decode('utf-8'))
        #frappe.msgprint("XML: {0}".format(xml_content))
        try:
            invoice = get_content_from_zugferd(xml_content.decode('utf-8'), debug=False)
            return invoice
        except Exception as err:
            frappe.log_error("ZUGFeRD parsing error: {0}".format(err), "Zugferd get_content_from_zugferd")
            return None
    except Exception as err:
        frappe.log_error("File not found. {0}".format(err), "Zugferd get_xml")

"""
Extracts the relevant content for a purchase invoice from a ZUGFeRD XML
:params:zugferd_xml:    xml content (string)
:return:                simplified dict with content
"""
def get_content_from_zugferd(zugferd_xml, debug=False):
    # create soup object
    soup = BeautifulSoup(zugferd_xml, 'lxml')
    # dict for invoice
    invoice = {}
    
    if suppliers_global_id:
        global_id_xml = soup.SpecifiedTradeProduct.GlobalID.get_text()
        suppliers_global_id = frappe.get_all('Supplier', filters={'supplier': global_id_xml}, fields = supplier_name[0])        
        invoice['supplier_name'] = soup.sellertradeparty.name.get_text()
        frappe.printmsg("Name of supplier is" + global_id_xml)
    elif suppliers_tax:
        tax_id_xml = soup.find_all(schemeID='VA')
        suppliers_tax = frappe.get_all('Supplier', filters={'supplier': tax_id_xml[0]}, fields = supplier_name[0])
        supplier = frappe.get_doc('Supplier', 'suppliers tax')       
        invoice['supplier_name'] = soup.sellertradeparty.name.get_text()
        supplier.global_id = soup.SpecifiedTradeProduct.GlobalID.get_text()
        supplier.save()
    else:
        tax_id_list = soup.find_all(schemeID='VA')
        # insert a new Suppler:
        frappe.db.insert({
        doctype: 'Supplier',
        supplier_name: soup.sellertradeparty.name.get_text(),
        tax_id: tax_id_list[0],
        global_id: soup.SpecifiedTradeProduct.GlobalID.get_text()
    })
    

    
    # get article information (items)
    invoice['items'] = soup.sellertradeparty.name.get_text()
    
    # dates (codes: UNCL 2379: 102=JJJJMMTT, 610=JJJJMM, 616=JJJJWW)
    try:
        invoice['posting_date'] = datetime.strptime(
            soup.issuedatetime.datetimestring.get_text(), "%Y%m%d")
    except Exception as err:
        if debug:
            print("Read posting date failed: {err}".format(err=err))
        pass
    return invoice
