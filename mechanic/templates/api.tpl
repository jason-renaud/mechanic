# do not modify - generated code at UTC {{ timestamp }}


def init_api(api):
    # imports need to be inside this method call to ensure models and controller objects are properly created in the
    # 'api' object
    from app import config
    # from controllers import {% for controller_name, controller in data.items() %}{{ controller_name }}{{ ", " if not loop.last }}{% endfor %}
    import controllers

    {%- for controller_name, controller in data.items() %}
    api.add_resource(_find_leaf_subclass(controllers.{{ controller_name }}), config["BASE_API_PATH"] + "{{ controller.uri.replace("{id}", "<string:resource_id>") }}")
    {%- endfor %}

def _find_leaf_subclass(cls):
    subclasses = cls.__subclasses__()
    ret_class = cls

    while subclasses:
        if len(subclasses) > 1:
            print("ERROR: More than 1 subclass defined for controller %s" % (cls))
            exit()
        else:
            ret_class = subclasses[0]
            subclasses = ret_class.__subclasses__()

            if len(subclasses) == 0:
                break
    return ret_class