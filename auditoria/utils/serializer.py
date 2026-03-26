# auditoria/utils/serializer.py

def model_to_dict(instance):
    data = {}

    for field in instance._meta.fields:
        field_name = field.name
        value = getattr(instance, field_name)

        try:
            data[field_name] = str(value)
        except:
            data[field_name] = None

    return data