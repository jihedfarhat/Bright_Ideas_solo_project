from flask import Flask, render_template, redirect, flash, request, session
from mysqlconnection import connectToMySQL
from flask_bcrypt import Bcrypt
import re
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = ("curtina")
bcrypt = Bcrypt(app) 
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')


@app.route("/main")
def login_registration_landing():
    return render_template("main.html")

@app.route("/register", methods=['POST'])
def register_user():
    is_valid = True

    if len(request.form['n']) < 2:
        is_valid = False
        flash("Name must be at least 2 characters long.")

    if len(request.form['a']) < 2:
        is_valid = False
        flash("Alias must be at least 2 characters long.")

    if len(request.form['pw']) < 8:
        is_valid = False
        flash("Password must be at least 8 characters.")

    if request.form['pw'] != request.form['c_pw']:
        is_valid = False
        flash("Passwords must match")

    if not EMAIL_REGEX.match(request.form['em']):
        is_valid = False
        flash("Please use a valid email.")

    if is_valid:
        encrypted_pw = bcrypt.generate_password_hash(request.form['pw'])

        mysql = connectToMySQL("bright_ideas")
        query = "INSERT INTO users (name, alias, email, password, created_at, updated_at) VALUES (%(n)s, %(a)s, %(e_m)s, %(p_w)s, NOW(), NOW())"
        data = {
            'n': request.form['n'],
            'a': request.form['a'],
            'e_m': request.form['em'],
            'p_w': encrypted_pw
        }
        session['user_id'] = mysql.query_db(query, data)
        return redirect("/bright_ideas")

    else:
        return redirect("/main")
        

@app.route("/")
def redirect_to_main():
    return redirect("/main")

@app.route("/login", methods=['POST'])
def login_user():

    is_valid = True
    if not request.form['em']:
        is_valid = False
        flash("Please enter an email.")
    
    if not EMAIL_REGEX.match(request.form['em']):
        is_valid = False
        flash("Please enter a valid email.")

    if not is_valid:
        return redirect("/main")


    else:
        mysql = connectToMySQL("bright_ideas")
        query = "SELECT * FROM users WHERE users.email = %(e_m)s"
        data = {'e_m': request.form['em']}
        user_info = mysql.query_db(query,data)
        print(user_info)

        if not user_info:
            return redirect("/main")
        
        if not request.form['pw']:
            is_valid = False
            flash("Please enter a password!")
            return redirect("/main")
        
        if not bcrypt.check_password_hash(user_info[0]['password'], request.form['pw']):
            is_valid = False
            flash("Password is not valid!")
            return redirect("/main")
        
        if is_valid:
            session['user_id'] = user_info[0]['user_id']
            return redirect("/bright_ideas")

        else:
            return redirect("/main")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/main")

##########################################

@app.route("/bright_ideas")
def ideas_landing():
    if 'user_id' not in session:
        return redirect("/")

    mysql = connectToMySQL("bright_ideas")
    query = "SELECT * FROM users WHERE users.user_id = %(uid)s"
    data = {
        'uid': session['user_id']
    }
    user = mysql.query_db(query, data)


    mysql = connectToMySQL("bright_ideas")
    #query = "SELECT ideas.idea_id, ideas.created_at, ideas.idea_content, users.name FROM ideas JOIN users on ideas.author = users.user_id ORDER BY created_at DESC"
    query = "SELECT ideas.author, ideas.idea_id, ideas.created_at, ideas.idea_content, users.alias FROM ideas JOIN users on ideas.author = users.user_id ORDER BY created_at DESC"
    ideas = mysql.query_db(query)


    mysql = connectToMySQL ("bright_ideas")
    query = "SELECT * FROM user_likes WHERE user_like = %(user_id)s"
    data = {
        'user_id': session['user_id']
    }
    liked_ideas = [idea['idea_like'] for idea in mysql.query_db(query, data) ]


    mysql = connectToMySQL("bright_ideas")
    query = "SELECT idea_like, COUNT(idea_like) as like_count FROM user_likes GROUP BY idea_like"
    like_count = mysql.query_db(query)

    for idea in ideas:

        # td = datetime.now() - idea['created_at']
        # if td.seconds == 0:
        #     idea['time_since_secs'] = 1
        # if td.seconds < 60 and td.seconds > 0:
        #     idea['time_since_secs'] = td.seconds
        # if td.seconds <  3600:
        #     idea['time_since_minutes'] = round(td.seconds / 60)
        # if td.seconds > 3600:
        #     idea['time_since_hours'] = round(td.seconds / 3600)
        # if td.days > 0:
        #     idea['time_since_days'] = td.days
        
        for like in like_count:
            if like['idea_like'] == idea['idea_id']:
                idea['like_count'] = like['like_count']

        if 'like_count' not in idea:
            idea['like_count'] = 0

    if user:
        return render_template("bright_ideas.html", user_data=user[0], idea_data=ideas, liked_ideas=liked_ideas)
    else:
        return redirect("/home")


@app.route("/process_idea", methods=["POST"])
def validate_proc_idea():
    is_valid = True
    if not request.form['idea_content']:
        flash("You cannot post an empty idea!")
        is_valid = False
    if len(request.form['idea_content']) > 255:
        flash("Ideas must be less than 255 characters.")
        is_valid = False

    if is_valid:
        mysql = connectToMySQL("bright_ideas")
        query = "INSERT INTO ideas (idea_content, created_at, updated_at, author) VALUES (%(content)s, NOW(), NOW(), %(author)s)"
        data = {
            'content': request.form['idea_content'],
            'author': session['user_id']
        }
        mysql.query_db(query, data)

    return redirect("/bright_ideas")


@app.route("/like_idea/<idea_id>")
def on_like(idea_id):
    mysql = connectToMySQL("bright_ideas")
    query = "INSERT INTO user_likes (user_like, idea_like) VALUES (%(user_id)s, %(idea_id)s)"
    data = {
        'user_id': session['user_id'],
        'idea_id': idea_id
    }
    _ = mysql.query_db(query, data)
    return redirect("/bright_ideas")


@app.route("/delete_idea/<idea_id>")
def on_delete(idea_id):
    mysql = connectToMySQL("bright_ideas")
    query = "DELETE FROM ideas WHERE idea_id = %(i_id)s AND author = %(u_id)s"
    data = {
        'i_id': idea_id,
        'u_id': session['user_id']
    }
    mysql.query_db(query, data)
    return redirect("/bright_ideas")


@app.route("/bright_ideas_details/<idea_id>")
def like_status(idea_id):

    mysql = connectToMySQL("bright_ideas")
    query = "SELECT ideas.idea_id, ideas.idea_content, users.name, users.alias FROM ideas JOIN users on ideas.author = users.user_id WHERE ideas.idea_id = %(i_id)s"
    data = {
        'i_id': idea_id
    }
    idea = mysql.query_db(query, data)
    if idea:
        idea = idea[0]
    
    mysql = connectToMySQL("bright_ideas")
    query = "SELECT users.alias, users.name FROM user_likes JOIN users ON user_likes.user_like = users.user_id WHERE idea_like = %(i_id)s"
    data = {
        'i_id': idea_id
    }
    user_who_have_liked = mysql.query_db(query, data)
    return render_template("like_status.html", idea=idea, user_who_have_liked=user_who_have_liked)


@app.route("/users/<int:user_id>")
def user_profile(user_id):
    try:
        mysql = connectToMySQL("bright_ideas")
        query = "SELECT users.user_id, users.name, users.alias, users.email, ideas.idea_content, ideas.idea_id FROM users JOIN ideas ON users.user_id = ideas.author WHERE users.user_id = %(u_id)s"
        data = {
            'u_id': user_id
        }
        user_info = mysql.query_db(query, data)
        
        if user_info:
            # Get the total number of posts for the user
            mysql = connectToMySQL("bright_ideas")
            query = "SELECT COUNT(*) AS user_post_count FROM ideas WHERE author = %(user_id)s"
            data = {
                'user_id': user_info[0]['user_id']
            }
            user_post_count = mysql.query_db(query, data)[0]['user_post_count']

            # Get the total number of likes for the user
            mysql = connectToMySQL("bright_ideas")
            query = "SELECT COUNT(*) AS user_like_count FROM user_likes WHERE user_like = %(user_id)s"
            data = {
                'user_id': user_info[0]['user_id']
            }
            user_like_count = mysql.query_db(query, data)[0]['user_like_count']

            return render_template("users.html", user_info=user_info, user_post_count=user_post_count, user_like_count=user_like_count)
        else:
            flash("User not found.")
            return redirect("/bright_ideas")
    except Exception as e:
        app.logger.error(f"Error in user_profile: {e}")
        return "An error occurred while processing the request.", 500



if __name__ == "__main__":
    app.run(debug=True)