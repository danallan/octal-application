from django import forms
from django.contrib.auth.hashers import check_password
from models import Graphs, Concepts
from utils import graphCheck, GraphIntegrityError

import json

class GraphForm(forms.ModelForm):
    json_input = forms.BooleanField(label=("JSON Input"), required=False,
            help_text=("Check this box to define the graph with raw JSON instead of the graph editor."))
    json_data = forms.CharField(label=("Graph JSON"), required=False,
            help_text=("Copy-paste or type the JSON representation of your graph here."),
            widget=forms.Textarea(attrs={'cols':80, 'rows':10}))

    def clean_json_data(self):
        """
        Validate JSON as being kmap structure
        """
        json_data = self.cleaned_data['json_data'].strip()
        if not json_data:
            raise forms.ValidationError("Error: graph cannot be blank")
        try: 
            graph_list = json.loads(json_data) 
            return graphCheck(graph_list)
        except ValueError:
            raise forms.ValidationError("Error: malformed JSON")
        except GraphIntegrityError as e:
            raise forms.ValidationError("Error: %(val)s", params={'val':e})

    class Meta:
        model = Graphs
        fields = ['name', 'description', 'public', 'study_active', 'json_input', 'json_data', 'lti_key', 'lti_secret', 'secret']
        labels = {
            'name': ("Unit Name"),
            'study_active': ("Research study"),
            'lti_key': ("Consumer Key"),
            'lti_secret': ("Shared Secret"),
        }
        help_texts = {
            'public': ("Public units are displayed on the unit list. Private units will be accessible by anyone with the URL."),
            'secret': ("The secret is used to modify the unit in the future. Please remember the value of this field!"),
            'study_active': ("Check this only if you plan to use this unit as part of a research investigation."),
        }
        widgets = {
            'name': forms.TextInput(attrs={'size':40}),
            'description': forms.Textarea(attrs={'cols':40, 'rows':2}),
            'secret': forms.HiddenInput(),
            'lti_key': forms.HiddenInput(),
            'lti_secret': forms.HiddenInput(),
        }

class KeyForm(forms.Form):
    """
    This form passes along data to ensure the user has authority to edit a map
    """
    secret = forms.CharField(max_length=16, label=("Secret Key"), 
                             widget=forms.TextInput(attrs={
                                 'autocomplete':'off',
                                 'autocorrect':'off',
                                 'autocapitalize':'off',
                                 'autofocus':'autofocus',
                                 }))
    edited = forms.BooleanField(required=False, initial=False, 
                                widget=forms.HiddenInput())

    def clean(self):
        """
        When validating the form, compare the key against the graph's secret
        """
        cleaned_data = super(KeyForm, self).clean()
        if not check_password(cleaned_data.get("secret"), self._graph.secret):
            raise forms.ValidationError("Incorrect secret")
        return cleaned_data

    def __init__(self, *args, **kwargs):
        self._graph = kwargs.pop('graph')
        super(KeyForm, self).__init__(*args, **kwargs)
