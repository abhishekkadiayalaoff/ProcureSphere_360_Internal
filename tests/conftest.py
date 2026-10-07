import django.template.context

# Python 3.14 compatibility patch for Django 4.2 BaseContext.__copy__
_original_context_copy = django.template.context.BaseContext.__copy__


def _fixed_context_copy(self):
    try:
        return _original_context_copy(self)
    except AttributeError:
        duplicate = object.__new__(self.__class__)
        duplicate.dicts = [d.copy() if isinstance(d, dict) else d for d in self.dicts]
        if hasattr(self, "_processors"):
            duplicate._processors = self._processors
        if hasattr(self, "_processors_index"):
            duplicate._processors_index = self._processors_index
        if hasattr(self, "request"):
            duplicate.request = self.request
        return duplicate


django.template.context.BaseContext.__copy__ = _fixed_context_copy
