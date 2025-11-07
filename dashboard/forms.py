from django import forms


class CompanySearchForm(forms.Form):
    company_name = forms.CharField(
        label='Company Name',
        max_length=255,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Enter a company name (e.g., Adani Power)',
                'class': 'form-control',
            }
        ),
    )

