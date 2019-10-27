import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from earnings import app, db, bcrypt, mail
from earnings.forms import (RegistrationForm, LoginForm, UpdateAccountForm,
                             PostForm, RequestResetForm, ResetPasswordForm)
from earnings.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
import stripe

pub_key = 'pk_test_giO1Kioq5GylE2dIQGlEfdHr006dHPTvzL'
secret_key = 'sk_test_qbHWikrWqzZRpqZZNJd81ICs00nSUtIKvp'

stripe.api_key = secret_key


@app.route("/")
@app.route("/home")
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('home.html', posts=posts)


@app.route("/daily")
def daily():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('daily.html', posts=posts)


@app.route("/blog")
def blog():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('blog.html', posts=posts)

@app.route("/ml")
def ml():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('ml.html', posts=posts)


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)




@app.route('/pay', methods=['POST'])
def pay():
    
    customer = stripe.Customer.create(email=request.form['stripeEmail'], source=request.form['stripeToken'])

    charge = stripe.Charge.create(
        customer=customer.id,
        amount=999,
        currency='usd',
        description='The AI Trade'
    )

    return redirect(url_for('register'))    


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(ticker=form.ticker.data, title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post')


@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.ticker = form.ticker.data
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.ticker.data = post.ticker
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


@app.route("/information_technology")
def information_technology():
    its=['Semiconductors', 'Data Processing & Outsourced Services','Communications Equipment','Electronic Components','Semiconductor Equipment',
        'IT Consulting & Other Services','Application Software','Technology Hardware, Storage & Peripherals','Electronic Equipment & Instruments',
        'Internet Services & Infrastructure','Electronic Manufacturing Services','Systems Software']
    return render_template('information_technology.html', its=its)

@app.route("/industrials")
def industrials():
    inds=['Industrial Machinery','Aerospace & Defense', 'Airlines','Industrial Conglomerates','Environmental & Facilities Services',
            'Building Products', 'Construction Machinery & Heavy Trucks','Research & Consulting Services','Railroads',
            'Trading Companies & Distributors', 'Trucking', 'Diversified Support Services', 'Air Freight & Logistics',
            'Agricultural & Farm Machinery','Construction & Engineering', 'Electrical Components & Equipment','Human Resource & Employment Services']
    return render_template('industrials.html', inds=inds)


@app.route("/health_care")
def health_care():
    hcs=['Life Sciences Tools & Services', 'Biotechnology', 'Health Care Technology', 'Health Care Services', 'Health Care Supplies', 
        'Health Care Equipment', 'Managed Health Care', 'Pharmaceuticals', 'Health Care Distributors', 'Health Care Facilities']
    return render_template('health_care.html', hcs=hcs)

@app.route("/communication_services")
def communication_services():
    coms=['Interactive Media & Services', 'Broadcasting', 'Publishing', 'Integrated Telecommunication Services', 'Interactive Home Entertainment', 
            'Cable & Satellite', 'Wireless Telecommunication Services', 'Movies & Entertainment', 'Advertising']
    return render_template('communication_services.html', coms=coms)

@app.route("/consumer_discretionary")
def consumer_discretionary():
    cds=['Internet & Direct Marketing Retail', 'Specialty Stores', 'Automobile Manufacturers', 'Hotels, Resorts & Cruise Lines', 'Household Appliances',
     'Homebuilding', 'Apparel, Accessories & Luxury Goods', 'Restaurants', 'Computer & Electronics Retail', 'General Merchandise Stores', 
     'Specialized Consumer Services', 'Apparel Retail', 'Home Improvement Retail', 'Department Stores', 'Automotive Retail', 
     'Auto Parts & Equipment', 'Home Furnishings', 'Motorcycle Manufacturers', 'Casinos & Gaming', 'Housewares & Specialties', 
     'Consumer Electronics', 'Distributors', 'Leisure Products']
    return render_template('consumer_discretionary.html', cds=cds)

@app.route("/consumer_staples")
def consumer_staples():
    css=['Packaged Foods & Meats','Soft Drinks','Tobacco','Distillers & Vintners','Hypermarkets & Super Centers','Food Retail',
        'Personal Products','Food Distributors','Household Products','Brewers','Drug Retail','Agricultural Products']
    return render_template('consumer_staples.html', css=css)

@app.route("/energy")
def energy():
    ens=['Oil & Gas Exploration & Production', 'Oil & Gas Refining & Marketing', 'Oil & Gas Equipment & Services', 
        'Oil & Gas Storage & Transportation', 'Oil & Gas Drilling', 'Integrated Oil & Gas']
    return render_template('energy.html', ens=ens)

@app.route("/financials")
def financials():
    fins=['Consumer Finance', 'Investment Banking & Brokerage', 'Asset Management & Custody Banks', 'Financial Exchanges & Data', 'Regional Banks',
     'Diversified Banks', 'Life & Health Insurance', 'Insurance Brokers', 'Multi-line Insurance', 'Property & Casualty Insurance', 
     'Thrifts & Mortgage Finance', 'Reinsurance']
    return render_template('financials.html', fins=fins)

@app.route("/materials")
def materials():
    mats=['Paper Packaging', 'Copper', 'Specialty Chemicals', 'Steel', 'Metal & Glass Containers', 'Fertilizers & Agricultural Chemicals', 
    'Construction Materials', 'Gold', 'Industrial Gases', 'Diversified Chemicals']
    return render_template('materials.html', mats=mats)

@app.route("/real_estate")
def real_estate():
    res=['Residential REITs', 'Office REITs', 'Industrial REITs', 'Hotel & Resort REITs', 'Health Care REITs', 'Specialized REITs', 
    'Retail REITs', 'Real Estate Services']
    return render_template('real_estate.html', res=res)

@app.route("/utilities")
def utilities():
    utis=['Multi-Utilities', 'Electric Utilities', 'Water Utilities', 'Gas Utilities', 'Independent Power Producers & Energy Traders']
    return render_template('utilities.html', utis=utis)

@app.route("/technicals")
def technicals():
    indicators=['SMA','EMA','WMA','DEMA','TEMA','TRIMA','KAMA','MAMA','T3','MACD','MACDEXT','STOCH','STOCHF', 'RSI',
            'STOCHRSI','WILLR','ADX','ADXR','APO','PPO','MOM','BOP','CCI','CMO','ROC','ROCR','AROON','AROONOSC','MFI',
            'TRIX','ULTOSC','DX','MINUS_DI','PLUS_DI','MINUS_DM','PLUS_DM','BBANDS','MIDPOINT','MIDPRICE','SAR','TRANGE',
            'ATR','NATR','AD','ADOSC','OBV','HT_TRENDLINE','HT_SINE','HT_TRENDMODE','HT_DCPERIOD','HT_DCPHASE','HT_PHASOR'
           ]
    return render_template('technicals.html', indicators=indicators)

@app.route("/agent", methods=['GET','POST'])
def agent():
    agents=['Turtle Trading agent','Moving Average agent', 'Signal Rolling agent','Policy Gradient agent','Q-learning agent','Evolution Strategy agent',
            'Double Q-learning agent','Recurrent Q-learning agent','Double Recurrent Q-learning agent','Duel Q-learning agent','Double Duel Q-learning agent','Duel Recurrent Q-learning agent','Double Duel Recurrent Q-learning agent','Actor-critic agent','Actor-critic Duel agent',
            'Actor-critic Recurrent agent','Actor-critic Duel Recurrent agent','Curiosity Q-learning agent','Recurrent Curiosity Q-learning agent',
            'Duel Curiosity Q-learning agent','Neuro-evoluton agent','Neuro-evoluton with Novelty Search agent','ABCD Strategy agent','Deep Evolution Strategy']
    ticker = request.form.get("ticker")

    return render_template('agent.html', agents=agents, ticker=ticker)


