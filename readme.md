# Trestle

## Setup

Make sure you have [Python 3](https://www.python.org/) installed.

Install [Poetry](https://poetry.eustace.io/docs/#installation).

### Optional

You don't have to use a front-end framework with Trestle.
The basic app can do everything it needs to server-side.

If you do want to go make something more JS heavy, then there are two main options described below.
You can always choose neither and roll your own, using Trestle as only the backend.

#### Svelte

[Svelte](https://svelte.dev/) requires everything to be set up and working - JS package management, builds, etc.
It is the most feature complete and modern option, but that comes with a lot of weight and overhead.
If you want to go in that direction, then you must also:

Install [Yarn](https://yarnpkg.com/lang/en/docs/install/).

#### Vue

[Vue](https://vuejs.org/) can be used without package management or a build system,
which gives you the advantage of being able to create a modern, reactive web app
without having to install nodejs or any other JS packages.
(And you can install all those things later, if you like.)
If you like this hybrid approach then there's nothing else to install.

### Get the Code

Clone the repository:

```bash
git clone git@github.com:bdoms/trestle.git

If you don't want to retain the history as part of your project I recommend this one line squash:

```bash
git reset $(git commit-tree HEAD^{tree} -m "Initial commit.")
```

### Dependencies

```bash
poetry install

yarn install
```

### Local Database Setup

Make sure postgres is installed (the last dependency on here is for psycopg2 support):

```bash
sudo apt install postgresql nginx supervisor libpq-dev
```

Then get into postgres:

```bash
sudo -u postgres psql
```

Create the local database and create a user to access it:

***WARNING! These values are provided as examples only. Do not use these in production!***

```sql
CREATE DATABASE trestle;
CREATE USER trestle_user WITH PASSWORD 'trestle_password';
GRANT ALL PRIVILEGES ON DATABASE trestle TO trestle_user;
```

Now modify the connection data at the top of `model.py` to reflect your local configuration.

Once that's done, build the tables for the first time by running the models file as a script:

```bash
python model.py
```

Repeat the above steps to setup a testing database:

```sql
CREATE DATABASE trestle_test;
CREATE USER trestle_test WITH PASSWORD 'trestle_test';
GRANT ALL PRIVILEGES ON DATABASE trestle_test TO trestle_test;
```

### Cleanup

Whatever you go with for javascript - no front end, Svelte, or Vue -
you'll have to make a few modifications to the code.
Particularly, in all cases, you'll need to modify `controllers/app.py` and the routes in `main.py`.

It's also a good idea to remove the files related to the other options as described below.

#### Remove Server Side

You'll need to remove the views.

```bash
rm views/user/auths.html
rm views/user/email.html
rm views/user/index.html
```

#### Remove Svelte

Simply remove the `svelte` folder and the JS package files.

```bash
rm -rf svelte
rm package.json
rm yarn.lock
```

#### Remove Vue

Remove the Vue html and js files, including the libraries.

```bash
rm views/vue.html
rm -rf static/j/lib
rm static/j/vue.js
```


## Use

### Mandatory Modifications

* Replace values for environment variables in `config/constants.py`
* In both cases:
  - Replace `SENDER_EMAIL` with the email address that emails should come from
  - Replace `SUPPORT_EMAIL` with the email address where you would like to receive support-related messages, such as error alerts
* Replace `YOU@YOUR_DOMAIN.com` in `views/static/terms.html` for DMCA compliance
* A sample Terms of Service and Privacy Policy have been provided as examples, but you are solely responsible for their content and how they apply to your site


### Going Forward

* Remember to escape any untrusted user content you display in templates
  - This happens by default, but always be careful, and you can use the `escape()` function to do it explicitly
* Add an entry to `views/sitemap.xml` for each page you want indexed by search engines
* Modify `static/robots.txt` to disallow any pages you don't want crawled (on a per branch basis)
* Enable and/or modify security features HSTS and CSP in `controllers/_base.py`
* Add new back end tests in `tests`
* If using Svelte, then add front end tests in `svelte/tests`
* After updating production, clear the cache and run migrations via `/dev`


### Common Commands

#### Run Local Development Server

Backend:

```bash
poetry shell
python main.py
```

##### If Using Svelte

You also need to run another command for the frontend in another terminal:

```bash
yarn start
```

Note that routing is handled by [page.js](https://visionmedia.github.io/page.js/)

#### Run Tests

```bash
python tests
```

Pass `--unit` or `--lint` as to only run unit tests or the linter, respectively.

You can also specify an individual file to run tests on, relative to the `tests` directory:

```bash
python tests test_default.py
```

##### Test with Svelte

You can run front end JS tests by:

```bash
yarn test
```

Learn about front end testing options with [Ava](https://github.com/avajs/ava/blob/master/docs/06-configuration.md).

#### Deploy to Production

##### Deploy with Svelte

Build first:

```bash
yarn build
```

You can fine tune builds with lots of options from [Parcel](https://parceljs.org/cli.html).
