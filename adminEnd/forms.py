from django import forms
from incidents.models import Beacon, BeaconProximity


class BeaconForm(forms.ModelForm):
    class Meta:
        model = Beacon
        fields = [
            'beacon_id', 'uuid', 'major', 'minor', 'location_name', 'building', 'floor', 'latitude', 'longitude', 'is_active'
        ]
        widgets = {
            'location_name': forms.TextInput(attrs={'class': 'form-control'}),
            'building': forms.TextInput(attrs={'class': 'form-control'}),
            'floor': forms.NumberInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'beacon_id': forms.TextInput(attrs={'class': 'form-control'}),
            'uuid': forms.TextInput(attrs={'class': 'form-control'}),
            'major': forms.NumberInput(attrs={'class': 'form-control'}),
            'minor': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BeaconProximityForm(forms.ModelForm):
    class Meta:
        model = BeaconProximity
        fields = ['to_beacon', 'priority']
        widgets = {
            'to_beacon': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def __init__(self, *args, from_beacon=None, **kwargs):
        super().__init__(*args, **kwargs)
        if from_beacon:
            # Exclude the source beacon from choices
            self.fields['to_beacon'].queryset = Beacon.objects.exclude(id=from_beacon.id)

    def clean_priority(self):
        p = self.cleaned_data.get('priority')
        if p is None or p < 1:
            raise forms.ValidationError('Priority must be a positive integer')
        return p

    def clean(self):
        data = super().clean()
        to_beacon = data.get('to_beacon')
        # from_beacon is set in the view before save so we cannot fully validate here
        return data