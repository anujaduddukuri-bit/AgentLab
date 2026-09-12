from django import forms


class AgentQueryForm(forms.Form):
    query = forms.CharField(
        label="Ask the Agent",
        min_length=2,
        max_length=4000,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Ask your question here...",
                "class": "input-area js-prompt",
            }
        ),
    )

    def clean_query(self):
        query = self.cleaned_data["query"].strip()
        if not query:
            raise forms.ValidationError("Please enter a question for the agent.")
        return query


class ToolPlaygroundForm(forms.Form):
    tool = forms.ChoiceField(
        label="Tool",
        widget=forms.Select(attrs={"class": "input-select"}),
    )
    input_data = forms.CharField(
        label="Input",
        required=False,
        max_length=8000,
        widget=forms.Textarea(
            attrs={
                "rows": 6,
                "placeholder": "Enter a value, city, query, JSON, or a JSON object of arguments.",
                "class": "input-area",
            }
        ),
    )

    def __init__(self, *args, tool_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tool"].choices = tool_choices or []

    def clean_input_data(self):
        return (self.cleaned_data.get("input_data") or "").strip()


class ChallengeQueryForm(forms.Form):
    query = forms.CharField(
        label="Your challenge query",
        min_length=2,
        max_length=4000,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Write the query you would send to the agent...",
                "class": "input-area js-prompt",
            }
        ),
    )

    def clean_query(self):
        query = self.cleaned_data["query"].strip()
        if not query:
            raise forms.ValidationError("Please submit a query for this challenge.")
        return query
