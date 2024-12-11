from django.dispatch import receiver
from pretix.base.signals import order_paid
from pretix.base.models import LogEntry
import requests
import json
from decouple import config
from collections import defaultdict

def authenticate():
    url = "https://www.app.webracun.com/rest/api/v1/login"
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({"username": config('WEBRACUN_USER'), "password": config('WEBRACUN_PASS')})
    response = requests.post(url, data=data, headers=headers)
    
    if response.status_code == 200:
        token = response.json()['token']
        return token
    else:
        return None

@receiver(order_paid)
def handle_order_creation(sender, order, **kwargs):
    token = authenticate()
    if token:
        # Group items by webRacunID
        items_grouped = defaultdict(int)

        for position in order.positions.all():
            metadata = position.item.meta_data
            web_racun_id = metadata.get('webRacunID')
            
            if web_racun_id and web_racun_id != '-1':  # Exclude items with webRacunID = -1
                items_grouped[web_racun_id] += 1

        # Prepare items for the Webracun API
        items = [{"itemId": web_racun_id, "quantity": str(quantity)} for web_racun_id, quantity in items_grouped.items()]

        print(items)

        if not items:
            print(f"No valid items to send for order {order.id}. Skipping Webracun invoice creation.")
            return

        url = "https://www.app.webracun.com/rest/api/v1/invoice"
        headers = {
            'Content-Type': 'application/json',
            'Authority': token
        }
        data = {
            "paymentType": "Card",
            "items": items
        }

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200:
            invoice_id = response.json().get('invoiceId', 'Unknown')
            LogEntry.objects.create(
                content_object=order,
                action_type=f"Invoice to Webracun {invoice_id} successfully created.",
            )
            print(f"Invoice {invoice_id} created successfully with items: {items}.")
        else:
            LogEntry.objects.create(
                content_object=order,
                action_type=f"Invoice to Webracun creation FAILED with status code {response.status_code}.",
            )
            print(f"Failed to create invoice for order {order.id}: {response.status_code}")
    else:
        print("Authentication failed.")
