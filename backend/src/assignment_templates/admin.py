"""Admin registrations for assignment template models."""

from django.contrib import admin

from .models import (
    AssignmentTemplate,
    McqChoice,
    McqCorrectAnswer,
    MultipleChoiceQuestion,
    NumberScaleQuestion,
    Question,
    ShortAnswerQuestion,
)


@admin.register(AssignmentTemplate)
class AssignmentTemplateAdmin(admin.ModelAdmin):
    """Admin configuration for assignment templates."""

    list_display = ("title", "grading_mode", "created_by_admin")
    search_fields = ("title",)
    list_filter = ("grading_mode",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin configuration for base questions."""

    list_display = ("id", "kind", "assignment_template", "auto_gradable", "graded")
    list_filter = ("kind", "auto_gradable", "graded")
    search_fields = ("prompt",)


admin.site.register(MultipleChoiceQuestion)
admin.site.register(ShortAnswerQuestion)
admin.site.register(NumberScaleQuestion)
admin.site.register(McqChoice)
admin.site.register(McqCorrectAnswer)
