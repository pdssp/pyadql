import pyadql


def define_env(env):
    env.variables["package_version"] = pyadql.__version__
    # Also expose it via config['extra'], since plugins other than
    # mkdocs-macros (e.g. mkdocs-with-pdf's cover template) only see
    # variables through the global mkdocs config, not through the
    # macros-specific Jinja environment.
    env.conf["extra"]["package_version"] = pyadql.__version__
