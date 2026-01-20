"""Admin registrations for submissions models."""

from django.contrib import admin

from .models import (
    Answer,
    MoodMeterAnswer,
    MultipleChoiceAnswer,
    MultipleChoiceSelected,
    NumberScaleAnswer,
    Response,
    ShortAnswerAnswer,
    Submission,
)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    """Admin configuration for submissions."""

    list_display = ("id", "assignment", "student", "status", "submitted_at")
    list_filter = ("status",)


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    """Admin configuration for answers."""

    list_display = ("id", "submission", "question", "answer_type", "skipped")
    list_filter = ("answer_type", "skipped")


admin.site.register(MultipleChoiceAnswer)
admin.site.register(MultipleChoiceSelected)
admin.site.register(ShortAnswerAnswer)
admin.site.register(NumberScaleAnswer)
admin.site.register(MoodMeterAnswer)
admin.site.register(Response)
