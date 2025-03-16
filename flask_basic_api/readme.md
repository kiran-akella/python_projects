![Flask](flask_image.png "flask")

# Why Flask is the Perfect Starting Point for Beginners in the API World ?

APIs (Application Programming Interfaces) are at the core of modern software development, allowing systems to communicate and share data seamlessly. If you’re just starting your journey into API development, Python’s Flask framework is one of the best places to begin.

**Why Flask?**

Flask is a lightweight, easy-to-use web framework for Python. It’s ideal for beginners because it has a simple, minimalistic design, meaning you can focus on learning the core concepts of web development without getting overwhelmed by unnecessary features.

**Benefits for Beginners:**

1. **Simplicity**: Flask’s minimalistic approach means you can build an API with just a few lines of code.
2. **Flexibility**: Start with small projects and scale them as you grow.
3. **Learning Core Concepts**: Flask helps you understand HTTP methods (GET, POST, PUT, DELETE), request handling, and response generation—skills that are valuable across any framework.
4. **Great Documentation**: Flask’s excellent documentation and active community make troubleshooting and learning easy.

# Building Your First Flask API:
Let’s look at an example of how to build a simple API with Flask:

# Step 1: Install Required Libraries

Make sure you have the necessary libraries installed:

``` bash
pip install Flask PyYAML Flask-HTTPAuth
```

# Step 2: Python Flask API Program

Here is the Python [Code](main.py "Flask program") for the Flask API that: 

- Stores data in a YAML file (data.yaml).
- Uses basic authentication with user credentials stored in another YAML file (users.yaml).
- Provides GET, POST, and PUT (update) methods.


# Explanation of the Code:
1. ## File Paths:
    - **DATA_FILE = 'data.yaml'** : This is where the key-value data is stored.
    - **USERS_FILE = 'users.yaml'**: This file stores the username and password pairs for authentication.

2. ## Functions:
    - **load_data():** Loads data from data.yaml. If the file doesn't exist, it returns an empty dictionary.
    - **save_data(data):** Saves data to data.yaml.
    - **load_users():** Loads users and passwords from users.yaml.
    - **verify_password(username, password):** This is the authentication callback function. It checks whether the provided username and password match any in the users.

3. ## Routes:
    - **GET /data/<key>:** Retrieves the value associated with a key.
    - **POST /data:** Adds a new key-value pair to the data.
    - **PUT /data/<key>:** Updates the value associated with an existing key.

4. ## Basic Authentication:
   - The @auth.login_required decorator ensures that every endpoint requires a valid username and password from the users.yaml file to access the data.

# Step 3: Create the users.yaml File

This file contains the user credentials (username and password).

**Example:** users.yaml

```yaml
admin: password123
user1: mypassword456
```

# Step 4: Create the data.yaml File

This file will be used to store key-value pairs.

Example data.yaml (initially empty or with some sample data):

``` yaml
some_key: some_value
```

# Step 5: Running the Flask App

To run the Flask API, execute the Python script:

```bash
python app.py
```

> The Flask server will run at http://127.0.0.1:5000/

# Example API Calls:

1. **GET Method**:
    - **URL**: http://127.0.0.1:5000/data/some_key
    - **Response**:

    ```json
    {"some_key": "some_value"}
    ```

    - **Authentication**:

    ```text
    Username: admin
    Password: password123
    ```

2. **POST Method**:
    - **URL**: http://127.0.0.1:5000/data
    - **Request Body**:

    ```json
    {
    "key": "new_key",
    "value": "new_value"
    }
    ```

    - **Response**:

    ```json
    {"message": "Data updated successfully"}
    ```

3. **PUT Method**:
    - **URL**: http://127.0.0.1:5000/data/some_key
    - **Request Body**:

    ```json
    {
    "value": "updated_value"
    }
    ```

    - **Response**:

    ```json
    {"message": "Data updated successfully"}
    ```

    - **Authentication**:

    ```text
    Username: admin
    Password: password123
    ```

# Notes:
- Make sure your users.yaml contains valid username/password pairs for authentication.
- The data.yaml file stores key-value pairs and will be created when the app first saves data.
- The authentication is done via basic HTTP authentication, so use a tool like curl or Postman to provide the Authorization header, or authenticate via browser prompts.

## Curl commands:
```bash
curl -X POST http://127.0.0.1:5000/data -u "kiran:github"  -H "Content-Type: application/json" -d '{"key":"bird", "value": "peacock"}'
```
```bash
curl -u "kiran:github" http://127.0.0.1:5000/data/bird
```
```bash
curl -X PUT http://127.0.0.1:5000/data/bird -u "kiran:github"  -H "Content-Type: application/json" -d '{"value": "swan"}'
```
