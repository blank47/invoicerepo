from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import fields, validate, post_load
from sqlalchemy import Sequence
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:admin12345@localhost/invoicedb'
db = SQLAlchemy(app)
ma = Marshmallow(app)

class InvoiceHeader(db.Model):
    Id = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    Date = db.Column(db.String)
    InvoiceNumber = db.Column(db.Integer, Sequence('invoice_number_seq'), unique=True)
    CustomerName = db.Column(db.String)
    BillingAddress = db.Column(db.String)
    ShippingAddress = db.Column(db.String)
    GSTIN = db.Column(db.String)
    TotalAmount = db.Column(db.Float)

class InvoiceItems(db.Model):
    Id = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    itemName = db.Column(db.String)
    Quantity = db.Column(db.Float)
    Price = db.Column(db.Float)
    Amount = db.Column(db.Float)

class InvoiceBillSundry(db.Model):
    Id = db.Column(db.String, primary_key=True, default=str(uuid.uuid4()))
    billSundryName = db.Column(db.String)
    Amount = db.Column(db.Float)

class InvoiceItemsSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = InvoiceItems
        load_instance = True

    @post_load
    def validate_amount(self, data, **kwargs):
        if data['Amount'] <= 0 or data['Quantity'] <= 0 or data['Price'] <= 0:
            raise ValueError('Amount, Quantity, and Price must be greater than zero.')
        return data

class InvoiceBillSundrySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = InvoiceBillSundry
        load_instance = True

class InvoiceHeaderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = InvoiceHeader
        load_instance = True

    items = fields.Nested(InvoiceItemsSchema, many=True)
    bill_sundries = fields.Nested(InvoiceBillSundrySchema, many=True)

    @post_load
    def validate_total_amount(self, data, **kwargs):
        total_amount = sum(item['Amount'] for item in data['items']) + sum(bill_sundry['Amount'] for bill_sundry in data['bill_sundries'])
        if data['TotalAmount'] != total_amount:
            raise ValueError('TotalAmount must be equal to the sum of the Amounts of the InvoiceItems and InvoiceBillSundries.')
        return data

invoice_header_schema = InvoiceHeaderSchema()
invoice_headers_schema = InvoiceHeaderSchema(many=True)

@app.route('/invoices', methods=['POST'])
def create_invoice():
    invoice = invoice_header_schema.load(request.json)
    db.session.add(invoice)
    db.session.commit()
    return invoice_header_schema.jsonify(invoice)

@app.route('/invoices/<id>', methods=['GET', 'PUT', 'DELETE'])
def handle_invoice(id):
    invoice = InvoiceHeader.query.get(id)
    if request.method == 'GET':
        return invoice_header_schema.jsonify(invoice)
    elif request.method == 'PUT':
        invoice = invoice_header_schema.load(request.json, instance=invoice)
        db.session.commit()
        return invoice_header_schema.jsonify(invoice)
    elif request.method == 'DELETE':
        db.session.delete(invoice)
        db.session.commit()
        return {'message': 'Invoice deleted successfully.'}

@app.route('/invoices', methods=['GET'])
def list_invoices():
    invoices = InvoiceHeader.query.all()
    return invoice_headers_schema.jsonify(invoices)

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
