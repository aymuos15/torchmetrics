# Copyright The Lightning team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from typing import Any, Optional, Union

from torch import Tensor
from typing_extensions import Literal

from torchmetrics.classification.base import _ClassificationTaskWrapper
from torchmetrics.classification.precision_recall_curve import (
    BinaryPrecisionRecallCurve,
    MulticlassPrecisionRecallCurve,
    MultilabelPrecisionRecallCurve,
)
from torchmetrics.functional.classification.sensitivity_specificity import (
    _binary_sensitivity_at_specificity_arg_validation,
    _binary_sensitivity_at_specificity_compute,
    _multiclass_sensitivity_at_specificity_arg_validation,
    _multiclass_sensitivity_at_specificity_compute,
    _multilabel_sensitivity_at_specificity_arg_validation,
    _multilabel_sensitivity_at_specificity_compute,
)
from torchmetrics.metric import Metric
from torchmetrics.utilities.data import dim_zero_cat as _cat
from torchmetrics.utilities.enums import ClassificationTask
from torchmetrics.utilities.imports import _MATPLOTLIB_AVAILABLE

if not _MATPLOTLIB_AVAILABLE:
    __doctest_skip__ = [
        "BinarySensitivityAtSpecificity.plot",
        "MulticlassSensitivityAtSpecificity.plot",
        "MultilabelSensitivityAtSpecificity.plot",
    ]


class BinarySensitivityAtSpecificity(BinaryPrecisionRecallCurve):
    r"""Compute the highest possible sensitivity value given the minimum specificity thresholds provided.

    This is done by first calculating the Receiver Operating Characteristic (ROC) curve for different thresholds and the
    find the sensitivity for a given specificity level.

    Accepts the following input tensors:

    - ``preds`` (float tensor): ``(N, ...)``. Preds should be a tensor containing probabilities or logits for each
      observation. If preds has values outside [0,1] range we consider the input to be logits and will auto apply
      sigmoid per element.
    - ``target`` (int tensor): ``(N, ...)``. Target should be a tensor containing ground truth labels, and therefore
      only contain {0,1} values (except if `ignore_index` is specified).

    Additional dimension ``...`` will be flattened into the batch dimension.

    The implementation both supports calculating the metric in a non-binned but accurate version and a binned version
    that is less accurate but more memory efficient. Setting the `thresholds` argument to `None` will activate the
    non-binned  version that uses memory of size :math:`\mathcal{O}(n_{samples})` whereas setting the `thresholds`
    argument to either an integer, list or a 1d tensor will use a binned version that uses memory of
    size :math:`\mathcal{O}(n_{thresholds})` (constant memory).

    Args:
        min_specificity: float value specifying minimum specificity threshold.
        thresholds:
            Can be one of:

            - ``None``, will use a non-binned approach where thresholds are dynamically calculated from
              all the data. It is the most accurate but also the most memory-consuming approach.
            - ``int`` (larger than 1), will use that number of thresholds linearly spaced from
              0 to 1 as bins for the calculation.
            - ``list`` of floats, will use the indicated thresholds in the list as bins for the calculation
            - 1d ``tensor`` of floats, will use the indicated thresholds in the tensor as
              bins for the calculation.

        validate_args: bool indicating if input arguments and tensors should be validated for correctness.
            Set to ``False`` for faster computations.
        kwargs: Additional keyword arguments, see :ref:`Metric kwargs` for more info.

    Returns:
        (tuple): a tuple of 2 tensors containing:

        - sensitivity: an scalar tensor with the maximum sensitivity for the given specificity level
        - threshold: an scalar tensor with the corresponding threshold level

    Example:
        >>> from torchmetrics.classification import BinarySensitivityAtSpecificity
        >>> from torch import tensor
        >>> preds = tensor([0, 0.5, 0.4, 0.1])
        >>> target = tensor([0, 1, 1, 1])
        >>> metric = BinarySensitivityAtSpecificity(min_specificity=0.5, thresholds=None)
        >>> metric(preds, target)
        (tensor(1.), tensor(0.1000))
        >>> metric = BinarySensitivityAtSpecificity(min_specificity=0.5, thresholds=5)
        >>> metric(preds, target)
        (tensor(0.6667), tensor(0.2500))

    """

    is_differentiable: bool = False
    higher_is_better: Optional[bool] = None
    full_state_update: bool = False
    plot_lower_bound: float = 0.0
    plot_upper_bound: float = 1.0

    def __init__(
        self,
        min_specificity: float,
        thresholds: Optional[Union[int, list[float], Tensor]] = None,
        ignore_index: Optional[int] = None,
        validate_args: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(thresholds, ignore_index, validate_args=False, **kwargs)
        if validate_args:
            _binary_sensitivity_at_specificity_arg_validation(min_specificity, thresholds, ignore_index)
        self.validate_args = validate_args
        self.min_specificity = min_specificity

    def compute(self) -> tuple[Tensor, Tensor]:  # type: ignore[override]
        """Compute metric."""
        state = (_cat(self.preds), _cat(self.target)) if self.thresholds is None else self.confmat
        return _binary_sensitivity_at_specificity_compute(state, self.thresholds, self.min_specificity)


class MulticlassSensitivityAtSpecificity(MulticlassPrecisionRecallCurve):
    r"""Compute the highest possible sensitivity value given the minimum specificity thresholds provided.

    This is done by first calculating the Receiver Operating Characteristic (ROC) curve for different thresholds and the
    find the sensitivity for a given specificity level.

    For multiclass the metric is calculated by iteratively treating each class as the positive class and all other
    classes as the negative, which is referred to as the one-vs-rest approach. One-vs-one is currently not supported by
    this metric.

    Accepts the following input tensors:

    - ``preds`` (float tensor): ``(N, C, ...)``. Preds should be a tensor containing probabilities or logits for each
      observation. If preds has values outside [0,1] range we consider the input to be logits and will auto apply
      softmax per sample.
    - ``target`` (int tensor): ``(N, ...)``. Target should be a tensor containing ground truth labels, and therefore
      only contain values in the [0, n_classes-1] range (except if `ignore_index` is specified).

    Additional dimension ``...`` will be flattened into the batch dimension.

    The implementation both supports calculating the metric in a non-binned but accurate version and a binned version
    that is less accurate but more memory efficient. Setting the `thresholds` argument to `None` will activate the
    non-binned  version that uses memory of size :math:`\mathcal{O}(n_{samples})` whereas setting the `thresholds`
    argument to either an integer, list or a 1d tensor will use a binned version that uses memory of
    size :math:`\mathcal{O}(n_{thresholds} \times n_{classes})` (constant memory).

    Args:
        num_classes: Integer specifying the number of classes
        min_specificity: float value specifying minimum specificity threshold.
        thresholds:
            Can be one of:

            - ``None``, will use a non-binned approach where thresholds are dynamically calculated from
              all the data. It is the most accurate but also the most memory-consuming approach.
            - ``int`` (larger than 1), will use that number of thresholds linearly spaced from
              0 to 1 as bins for the calculation.
            - ``list`` of floats, will use the indicated thresholds in the list as bins for the calculation
            - 1d ``tensor`` of floats, will use the indicated thresholds in the tensor as
              bins for the calculation.

        validate_args: bool indicating if input arguments and tensors should be validated for correctness.
            Set to ``False`` for faster computations.
        kwargs: Additional keyword arguments, see :ref:`Metric kwargs` for more info.

    Returns:
        (tuple): a tuple of either 2 tensors or 2 lists containing

        - sensitivity: an 1d tensor of size (n_classes, ) with the maximum sensitivity for the given
            specificity level per class
        - thresholds: an 1d tensor of size (n_classes, ) with the corresponding threshold level per class


    Example:
        >>> from torchmetrics.classification import MulticlassSensitivityAtSpecificity
        >>> from torch import tensor
        >>> preds = tensor([[0.75, 0.05, 0.05, 0.05, 0.05],
        ...                 [0.05, 0.75, 0.05, 0.05, 0.05],
        ...                 [0.05, 0.05, 0.75, 0.05, 0.05],
        ...                 [0.05, 0.05, 0.05, 0.75, 0.05]])
        >>> target = tensor([0, 1, 3, 2])
        >>> metric = MulticlassSensitivityAtSpecificity(num_classes=5, min_specificity=0.5, thresholds=None)
        >>> metric(preds, target)
        (tensor([1., 1., 0., 0., 0.]), tensor([0.7500, 0.7500, 1.0000, 1.0000, 1.0000]))
        >>> metric = MulticlassSensitivityAtSpecificity(num_classes=5, min_specificity=0.5, thresholds=5)
        >>> metric(preds, target)
        (tensor([1., 1., 0., 0., 0.]), tensor([0.7500, 0.7500, 1.0000, 1.0000, 1.0000]))

    """

    is_differentiable: bool = False
    higher_is_better: Optional[bool] = None
    full_state_update: bool = False
    plot_lower_bound: float = 0.0
    plot_upper_bound: float = 1.0
    plot_legend_name: str = "Class"

    def __init__(
        self,
        num_classes: int,
        min_specificity: float,
        thresholds: Optional[Union[int, list[float], Tensor]] = None,
        ignore_index: Optional[int] = None,
        validate_args: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            num_classes=num_classes, thresholds=thresholds, ignore_index=ignore_index, validate_args=False, **kwargs
        )
        if validate_args:
            _multiclass_sensitivity_at_specificity_arg_validation(
                num_classes, min_specificity, thresholds, ignore_index
            )
        self.validate_args = validate_args
        self.min_specificity = min_specificity

    def compute(self) -> tuple[Tensor, Tensor]:  # type: ignore[override]
        """Compute metric."""
        state = (_cat(self.preds), _cat(self.target)) if self.thresholds is None else self.confmat
        return _multiclass_sensitivity_at_specificity_compute(
            state, self.num_classes, self.thresholds, self.min_specificity
        )


class MultilabelSensitivityAtSpecificity(MultilabelPrecisionRecallCurve):
    r"""Compute the highest possible sensitivity value given the minimum specificity thresholds provided.

    This is done by first calculating the Receiver Operating Characteristic (ROC) curve for different thresholds and the
    find the sensitivity for a given specificity level.

    Accepts the following input tensors:

    - ``preds`` (float tensor): ``(N, C, ...)``. Preds should be a tensor containing probabilities or logits for each
      observation. If preds has values outside [0,1] range we consider the input to be logits and will auto apply
      sigmoid per element.
    - ``target`` (int tensor): ``(N, C, ...)``. Target should be a tensor containing ground truth labels, and therefore
      only contain {0,1} values (except if `ignore_index` is specified).

    Additional dimension ``...`` will be flattened into the batch dimension.

    The implementation both supports calculating the metric in a non-binned but accurate version and a binned version
    that is less accurate but more memory efficient. Setting the `thresholds` argument to `None` will activate the
    non-binned  version that uses memory of size :math:`\mathcal{O}(n_{samples})` whereas setting the `thresholds`
    argument to either an integer, list or a 1d tensor will use a binned version that uses memory of
    size :math:`\mathcal{O}(n_{thresholds} \times n_{labels})` (constant memory).

    Args:
        num_labels: Integer specifying the number of labels
        min_specificity: float value specifying minimum specificity threshold.
        thresholds:
            Can be one of:

            - ``None``, will use a non-binned approach where thresholds are dynamically calculated from
              all the data. It is the most accurate but also the most memory-consuming approach.
            - ``int`` (larger than 1), will use that number of thresholds linearly spaced from
              0 to 1 as bins for the calculation.
            - ``list`` of floats, will use the indicated thresholds in the list as bins for the calculation
            - 1d ``tensor`` of floats, will use the indicated thresholds in the tensor as
              bins for the calculation.

        validate_args: bool indicating if input arguments and tensors should be validated for correctness.
            Set to ``False`` for faster computations.
        kwargs: Additional keyword arguments, see :ref:`Metric kwargs` for more info.

    Returns:
        (tuple): a tuple of either 2 tensors or 2 lists containing

        - sensitivity: an 1d tensor of size ``(n_classes, )`` with the maximum sensitivity for the given
            specificity level per class
        - thresholds: an 1d tensor of size ``(n_classes, )`` with the corresponding threshold level per class

    Example:
        >>> from torchmetrics.classification import MultilabelSensitivityAtSpecificity
        >>> from torch import tensor
        >>> preds = tensor([[0.75, 0.05, 0.35],
        ...                 [0.45, 0.75, 0.05],
        ...                 [0.05, 0.55, 0.75],
        ...                 [0.05, 0.65, 0.05]])
        >>> target = tensor([[1, 0, 1],
        ...                  [0, 0, 0],
        ...                  [0, 1, 1],
        ...                  [1, 1, 1]])
        >>> metric = MultilabelSensitivityAtSpecificity(num_labels=3, min_specificity=0.5, thresholds=None)
        >>> metric(preds, target)
        (tensor([0.5000, 1.0000, 0.6667]), tensor([0.7500, 0.5500, 0.3500]))
        >>> metric = MultilabelSensitivityAtSpecificity(num_labels=3, min_specificity=0.5, thresholds=5)
        >>> metric(preds, target)
        (tensor([0.5000, 1.0000, 0.6667]), tensor([0.7500, 0.5000, 0.2500]))

    """

    is_differentiable: bool = False
    higher_is_better: Optional[bool] = None
    full_state_update: bool = False
    plot_lower_bound: float = 0.0
    plot_upper_bound: float = 1.0
    plot_legend_name: str = "Label"

    def __init__(
        self,
        num_labels: int,
        min_specificity: float,
        thresholds: Optional[Union[int, list[float], Tensor]] = None,
        ignore_index: Optional[int] = None,
        validate_args: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            num_labels=num_labels, thresholds=thresholds, ignore_index=ignore_index, validate_args=False, **kwargs
        )
        if validate_args:
            _multilabel_sensitivity_at_specificity_arg_validation(num_labels, min_specificity, thresholds, ignore_index)
        self.validate_args = validate_args
        self.min_specificity = min_specificity

    def compute(self) -> tuple[Tensor, Tensor]:  # type: ignore[override]
        """Compute metric."""
        state = (_cat(self.preds), _cat(self.target)) if self.thresholds is None else self.confmat
        return _multilabel_sensitivity_at_specificity_compute(
            state, self.num_labels, self.thresholds, self.ignore_index, self.min_specificity
        )


class SensitivityAtSpecificity(_ClassificationTaskWrapper):
    r"""Compute the highest possible sensitivity value given the minimum specificity thresholds provided.

    This is done by first calculating the Receiver Operating Characteristic (ROC) curve for different thresholds and the
    find the sensitivity for a given specificity level.

    This function is a simple wrapper to get the task specific versions of this metric, which is done by setting the
    ``task`` argument to either ``'binary'``, ``'multiclass'`` or ``'multilabel'``. See the documentation of
    :class:`~torchmetrics.classification.BinarySensitivityAtSpecificity`,
    :class:`~torchmetrics.classification.MulticlassSensitivityAtSpecificity` and
    :class:`~torchmetrics.classification.MultilabelSensitivityAtSpecificity` for the specific details of each argument
    influence and examples.

    """

    def __new__(  # type: ignore[misc]
        cls: type["SensitivityAtSpecificity"],
        task: Literal["binary", "multiclass", "multilabel"],
        min_specificity: float,
        thresholds: Optional[Union[int, list[float], Tensor]] = None,
        num_classes: Optional[int] = None,
        num_labels: Optional[int] = None,
        ignore_index: Optional[int] = None,
        validate_args: bool = True,
        **kwargs: Any,
    ) -> Metric:
        """Initialize task metric."""
        task = ClassificationTask.from_str(task)
        if task == ClassificationTask.BINARY:
            return BinarySensitivityAtSpecificity(min_specificity, thresholds, ignore_index, validate_args, **kwargs)
        if task == ClassificationTask.MULTICLASS:
            if not isinstance(num_classes, int):
                raise ValueError(f"`num_classes` is expected to be `int` but `{type(num_classes)} was passed.`")
            return MulticlassSensitivityAtSpecificity(
                num_classes, min_specificity, thresholds, ignore_index, validate_args, **kwargs
            )
        if task == ClassificationTask.MULTILABEL:
            if not isinstance(num_labels, int):
                raise ValueError(f"`num_labels` is expected to be `int` but `{type(num_labels)} was passed.`")
            return MultilabelSensitivityAtSpecificity(
                num_labels, min_specificity, thresholds, ignore_index, validate_args, **kwargs
            )
        raise ValueError(f"Task {task} not supported!")
