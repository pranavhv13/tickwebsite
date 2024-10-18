from django import forms
from .models import FormConfig

def create_dynamic_form(form_id,max_members=0):
    class DynamicForm(forms.Form):
        form_config = FormConfig.objects.get(id=form_id)
        config = form_config.fields 
        field_data = config.get('fields', [])

        # Add members choice field if multiple_members_required is true
        if max_members is not 0 and max_members > 1:
            locals()['number_of_members'] = forms.ChoiceField(
                label="Number of Members",
                choices=[(i, str(i)) for i in range(1, max_members + 1)],
                required=True
            )

        for field in field_data:
            field_type = field['type']
            is_required = field.get('required', True)  # Default to True if 'required' key is not present

            if field_type == 'text':
                locals()[field['name']] = forms.CharField(label=field['label'], required=is_required)
            
            elif field_type == 'email':
                locals()[field['name']] = forms.EmailField(label=field['label'], required=is_required)
            
            elif field_type == 'textarea':
                locals()[field['name']] = forms.CharField(widget=forms.Textarea, label=field['label'], required=is_required)
            
            elif field_type == 'number':
                locals()[field['name']] = forms.IntegerField(label=field['label'], required=is_required)
            
            elif field_type == 'image':
                locals()[field['name']] = forms.ImageField(label=field['label'], required=is_required)
            
            elif field_type == 'file': 
                locals()[field['name']] = forms.FileField(label=field['label'], required=is_required) 
            
            elif field_type == 'date':  # Adjusted date field for date selection
                locals()[field['name']] = forms.DateField(
                    label=field['label'],
                    required=is_required,
                    widget=forms.DateInput(attrs={'type': 'date'})  # Using HTML5 date input
                )
            
            elif field_type == 'select':  # Handle choice field
                choices = field.get('choices', [])  # Expecting a 'choices' key in the field definition
                choice_list = [(choice['value'], choice['label']) for choice in choices]
                locals()[field['name']] = forms.ChoiceField(choices=choice_list, label=field['label'], required=is_required)
            # You can add more field types here
        
    return DynamicForm


