import yaml

def read_yaml(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

if __name__ == "__main__":
    config = read_yaml("config.yaml")
    print(config)
    