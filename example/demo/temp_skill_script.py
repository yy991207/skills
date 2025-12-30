# This Python script will generate an HTML file for a distinctive, production-grade login page.
# The aesthetic direction is inspired by a futuristic, minimalistic design with a touch of luxury.

import os

# Define the content of the HTML file
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Luxury Login</title>
    <style>
        :root {
            --primary-color: #1a1a1a;
            --secondary-color: #f5f5f5;
            --accent-color: #ffcc00;
            --font-display: 'Bebas Neue', cursive;
            --font-body: 'Roboto', sans-serif;
        }
        body {
            background: var(--primary-color);
            color: var(--secondary-color);
            font-family: var(--font-body);
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .login-container {
            background: var(--secondary-color);
            padding: 4rem;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.3);
            text-align: center;
            width: 300px;
        }
        .login-container h1 {
            font-family: var(--font-display);
            font-size: 2.5rem;
            color: var(--primary-color);
            margin-bottom: 2rem;
        }
        .input-group {
            margin-bottom: 1.5rem;
        }
        .input-group input {
            width: 100%;
            padding: 0.8rem;
            border: none;
            border-radius: 5px;
            font-size: 1rem;
        }
        .input-group button {
            width: 100%;
            padding: 0.8rem;
            border: none;
            border-radius: 5px;
            background: var(--accent-color);
            color: var(--primary-color);
            font-size: 1rem;
            cursor: pointer;
            transition: background 0.3s ease;
        }
        .input-group button:hover {
            background: #e6b800;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>Login</h1>
        <form>
            <div class="input-group">
                <input type="text" placeholder="Username" required>
            </div>
            <div class="input-group">
                <input type="password" placeholder="Password" required>
            </div>
            <div class="input-group">
                <button type="submit">Login</button>
            </div>
        </form>
    </div>
</body>
</html>
"""

# Define the file path
file_path = "luxury_login.html"

# Write the HTML content to the file
with open(file_path, "w", encoding="utf-8") as file:
    file.write(html_content)

print(f"Login page created and saved as {file_path}")