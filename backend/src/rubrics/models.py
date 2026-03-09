"""Rubric models for defining grading criteria.

Rubrics are first-class entities separate from assessments. They define
structured grading criteria with weighted criteria and scored levels.

Model Hierarchy:
    Rubric
        └── RubricCriterion (ordered, weighted)
            └── RubricLevel (ordered, scored)
"""

from django.db import models

from accounts.models import User


class RubricStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"


class Rubric(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=RubricStatus.choices, default=RubricStatus.ACTIVE
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, db_column="created_by_id"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rubrics"

    def __str__(self):
        return self.title


class RubricCriterion(models.Model):
    rubric = models.ForeignKey(
        Rubric, on_delete=models.CASCADE, related_name="criteria"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    order_index = models.IntegerField()
    weight = models.FloatField(default=1.0)

    class Meta:
        db_table = "rubric_criteria"
        unique_together = [("rubric", "order_index")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(weight__gt=0),
                name="rubric_criterion_weight_positive",
            )
        ]

    def __str__(self):
        return f"{self.rubric.title}: {self.title}"


class RubricLevel(models.Model):
    criterion = models.ForeignKey(
        RubricCriterion, on_delete=models.CASCADE, related_name="levels"
    )
    label = models.CharField(max_length=255)
    points = models.FloatField()
    description = models.TextField(blank=True, default="")
    order_index = models.IntegerField()

    class Meta:
        db_table = "rubric_levels"
        unique_together = [("criterion", "order_index")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(points__gte=0),
                name="rubric_level_points_non_negative",
            )
        ]

    def __str__(self):
        return f"{self.criterion.title}: {self.label} ({self.points}pts)"
