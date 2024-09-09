from django.dispatch import receiver
from pretix.base.signals import order_placed
from pretix.base.models import LogEntry
import requests
import json

def authenticate():
    url = "https://www.app.webracun.com/rest/api/v1/login"
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({"username": "user", "password": "pass"})
    response = requests.post(url, data=data, headers=headers)
    print("-----------------------")
    response_json = response.json() 
    print(json.dumps(response_json, indent=4))      
    print("-----------------------")

    
    if response.status_code == 200:
        token = response.json()['token']
        return token
    else:
        return None

@receiver(order_placed)
def handle_order_creation(sender, order, **kwargs):
    token = authenticate()
    if token:
        item_quantity = order.positions.count() 
        url = "https://www.app.webracun.com/rest/api/v1/invoice"
        headers = {
            'Content-Type': 'application/json',
            'Authority': token 
        }
        data = {
            "paymentType": "Card", 
            "items": [
                {"itemId": "1", "quantity": str(item_quantity)} 
            ]
        }
        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200:
            invoice_id = response.json().get('invoiceId', 'Unknown')
            LogEntry.objects.create(
                content_object=order,
                action_type=f"Invoice to Webracun {invoice_id} successfully created.",
            )
            print(f"Invoice {invoice_id} created successfully with quantity {item_quantity}.")
        else:
            LogEntry.objects.create(
                content_object=order,
                action_type=f"Invoice to Webracun creation FAILED with status code {response.status_code}.",
            )
            print(f"Failed to create invoice for order {order.id}: {response.status_code}")
    else:
        print("Authentication failed.")
