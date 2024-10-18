import base64,qrcode,json,hashlib,requests,random,string
from PIL import Image, ImageDraw, ImageFont
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from valid_entry import settings
from .models import Event, FormConfig, Ticket
from .forms import create_dynamic_form


#  for phonepe payment gateway
def generate_checksum(data, salt_key, salt_index):
    """Generate checksum for payment."""
    checksum_str = data + '/pg/v1/pay' + salt_key
    checksum = hashlib.sha256(checksum_str.encode()).hexdigest() + '###' + salt_index
    return checksum

def generate_ids(ticket_id):
    """Generate merchantTransactionId and merchantUserId based on the ticket_id."""
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    merchant_transaction_id = f"TXN{random_part}-{ticket_id}"
    merchant_user_id = f"USR{random_part}_{ticket_id}"
    
    return merchant_transaction_id, merchant_user_id

# View functions
def index(request):
    """Render index page."""
    return render(request, 'index.html')

def contact(request):
    """Render contact page."""
    return render(request, 'contact.html')

def ticket_scan(request):
    """Render ticket scan page."""
    return render(request, 'tk_scan.html')


def events(request):
    """Render events page with upcoming and completed events."""
    upcoming_events = Event.objects.filter(isDone=False).order_by('date')
    completed_events = Event.objects.filter(isDone=True).order_by('-date')
    return render(request, 'events.html', {
        'upcoming_events': upcoming_events,
        'completed_events': completed_events,
    })


def event_info(request, event_id):
    """Render event information page."""
    event = Event.objects.get(id=event_id)
    return render(request, 'event_info.html', {'event': event})


@csrf_exempt
def register_event(request, event_id, form_id):
    """Handle event registration and payment initiation."""
    event = get_object_or_404(Event, id=event_id)
    form_config = get_object_or_404(FormConfig, id=form_id)
    FORM_CONFIGS = form_config.fields

    # Create the dynamic form
    DynamicForm = create_dynamic_form(form_id,event.max_members)

    if request.method == 'POST':
        form = DynamicForm(request.POST, request.FILES)
        if form.is_valid():
            submitted_data = form.cleaned_data
            # Get the number of members from the submitted data
            no_of_members = int(submitted_data.get('number_of_members', 1))

            # Handle file/image or date fields
            uploaded_file = None
            file_field_name = None
            uploaded_date = None
            date_field_name = None

            for field in FORM_CONFIGS['fields']:
                if field['type'] == 'image' or field['type'] == 'file':  # File or image field
                    file_field_name = field['name']
                    uploaded_file = request.FILES.get(file_field_name)

            for field in FORM_CONFIGS['fields']:
                if field['type'] == 'date':  # Date field
                    date_field_name = field['name']
                    uploaded_date = submitted_data.get(date_field_name)

            # Create a unique ticket ID and encrypt it
            ticket_id = f"evt_{event_id}_tk_{Ticket.objects.count() + 1}"
            byte_string = ticket_id.encode('utf-8')
            base64_bytes = base64.b64encode(byte_string)
            enc_tk_id = base64_bytes.decode('utf-8')
            

            # Save ticket details to the Ticket model
            ticket = Ticket.objects.create(
                ticket_id=ticket_id,
                enc_tk_id=enc_tk_id,
                event_id=event,
                ticket_data={k: v for k, v in submitted_data.items() if k != file_field_name and k != date_field_name},
                uploaded_file=uploaded_file,
                date_field=uploaded_date,
                no_of_members=no_of_members
            )

            if event.payment_required:

                # Payment initiation
                merchant_transaction_id, merchant_user_id = generate_ids(ticket_id)
                
                if(event.multiple_members_required):
                    amount = event.event_amount * int(no_of_members)
                else:
                    amount = event.event_amount
                callback_url = 'http://127.0.0.1:8000/payment_callback'
                payload = {
                    "merchantId": settings.PHONEPE_MERCHANT_ID,
                    "merchantTransactionId": merchant_transaction_id,
                    "merchantUserId": merchant_user_id,
                    "amount": amount * 100,  # In paisa
                    "redirectUrl": callback_url,
                    "redirectMode": "POST",
                    "callbackUrl": callback_url,
                    "mobileNumber": "9448139108",
                    "paymentInstrument": {"type": "PAY_PAGE"}
                }
                print("Payload:", payload)

                data = base64.b64encode(json.dumps(payload).encode()).decode()
                print("Encoded Data:", data)
                checksum = generate_checksum(data, settings.PHONEPE_MERCHANT_KEY, settings.SALT_INDEX)
                final_payload = {"request": data}

                headers = {
                    'Content-Type': 'application/json',
                    'X-VERIFY': checksum,
                }

                try:
                    response = requests.post(settings.PHONEPE_INITIATE_PAYMENT_URL, headers=headers,
                                             json=final_payload)
                    print("Response status code:", response.status_code)
                    print("Response text:", response.text)

                    try:
                        data = response.json()  # Safely convert the response to JSON
                        print("Response JSON:", data)

                        if data.get('success'):
                            # Handle GET method for redirection
                            redirect_info = data['data']['instrumentResponse']['redirectInfo']
                            if redirect_info['method'] == 'GET':
                                return redirect(redirect_info['url'])
                            else:
                                return HttpResponse(f"Unexpected redirect method: {redirect_info['method']}")
                        else:
                            return HttpResponse(f"PhonePe payment gateway error: {data.get('message')}")
                    except ValueError:
                        # Response is not JSON, handle it
                        return HttpResponse(f"Invalid response from PhonePe: {response.text}")

                except requests.RequestException as e:
                    return HttpResponse(f"PhonePe payment gateway exception: {e}")

            else:

                response = render(request, 'sucess.html', {
                    'submitted_data': ticket.ticket_data,
                    'ticket_id': ticket.ticket_id,
                })
                return response

    else:
        form = DynamicForm()

    return render(request, 'register_event.html', {
        'event': event,
        'form': form,
        'title': FORM_CONFIGS['title'],
        'form_id': form_id,
        'event_form_id': event.form_id
    })


@csrf_exempt
def payment_callback(request):
    if request.method != 'POST':
        return HttpResponse("request.method != 'POST' in payment_callback view")

    try:
        # Convert POST data to a dictionary and log it
        data = request.POST.dict()
        transactionID = data.get('transactionId')
        transactionID = transactionID[14:]

        ticket = get_object_or_404(Ticket, ticket_id = transactionID)
        print(f"eveny.id-------------------{ticket.event_id}")
        event = get_object_or_404(Event, title = ticket.event_id)

        # Check if checksum and payment code are valid
        if data.get('checksum') and data.get('code') == "PAYMENT_SUCCESS":
            ticket.is_paid = True
            ticket.payment_response = data
            event.tickets_available = event.tickets_available - ticket.no_of_members
            ticket.save()
            event.save()
            # Render success page with ticket data
            response = render(request, 'sucess.html', {
                'submitted_data': ticket.ticket_data,
                'ticket_id': ticket.ticket_id,
            })
            return response

        else:
            return render(request, 'failed.html')

    except Exception as e:
        return HttpResponse(f"Exception in payment_callback view : {e}")

def download_ticket(request, ticket_id):
    """Generate and download the event ticket with QR code."""
    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
    event = ticket.event_id
    enc_tk_id = ticket.enc_tk_id
    qr_enc = f"www.valid-entry.in/tk/{enc_tk_id}"

    # Create QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_enc)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    # Create ticket image
    ticket_image = Image.open('static/ticket.jpg')
    draw = ImageDraw.Draw(ticket_image)

    # Define fonts (adjust font path if needed)
    title_font = ImageFont.load_default(size=20)
    detail_font = ImageFont.load_default()

    # Draw event name and ticket ID on the ticket image
    center_x, center_y = 150, 100
    event_text = f"Event: {event.title}"
    bbox = draw.textbbox((0, 0), event_text, font=title_font)
    text_width = bbox[2] - bbox[0]
    x_position = center_x - (text_width // 2)
    draw.text((x_position, center_y), event_text, fill="white", font=title_font)
    draw.text((125, 425), f"{ticket_id}", fill="black", font=detail_font)

    # Paste the QR code onto the ticket image
    qr_img = qr_img.resize((170, 170))
    ticket_image.paste(qr_img, (65, 150))

    # Save and return the ticket image
    ticket_image_path = f'media/tickets/{ticket_id}.png'
    ticket_image.save(ticket_image_path, format='PNG')

    with open(ticket_image_path, 'rb') as img_file:
        response = HttpResponse(img_file.read(), content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="{ticket_id}.png"'
        return response



