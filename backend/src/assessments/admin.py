"""Admin registrations for assessments models."""

from django.contrib import admin

from .models import (
    Assessment,
    McqChoice,
    McqCorrectAnswer,
    MoodMeterLabel,
    MoodMeterQuestion,
    MultipleChoiceQuestion,
    NumberScaleQuestion,
    Question,
    ShortAnswerQuestion,
)


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    """Admin configuration for assessments."""

    list_display = ("title", "grading_mode", "created_by_admin")
    search_fields = ("title",)
    list_filter = ("grading_mode",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin configuration for base questions."""

    list_display = ("id", "kind", "assessment", "auto_gradable", "graded")
    list_filter = ("kind", "auto_gradable", "graded")
    search_fields = ("prompt",)


admin.site.register(MultipleChoiceQuestion)
admin.site.register(ShortAnswerQuestion)
admin.site.register(NumberScaleQuestion)
admin.site.register(MoodMeterQuestion)
admin.site.register(McqChoice)
admin.site.register(McqCorrectAnswer)
admin.site.register(MoodMeterLabel)
