# Trestle

Copyright &copy; 2019, [Brendan Doms](https://www.bdoms.com/)  
Licensed under the [MIT license](http://www.opensource.org/licenses/MIT)

A jumping off point for building modern web apps.

Uses Python 3, Tornado, and Peewee on the back end, with Vue, Svelte, or no JaaScript on the front end.

## Setup

Make sure you have [Python 3](https://www.python.org/) installed.

Install [Poetry](https://poetry.eustace.io/docs/#installation).

### Optional

You don't have to use a front end framework with Trestle.
The basic app can do everything it needs to server-side.

If you do want to go make something more JS heavy, then there are two main options described below.
You can always choose neither and roll your own, using Trestle as only the back end.

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
```

If you don't want to retain the history as part of your project then we recommend this one line squash:

```bash
git reset $(git commit-tree HEAD^{tree} -m "Initial commit.")
```

### Dependencies

```bash
poetry install
```

#### Svelte Dependencies

```bash
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

Now modify the connection data in `config/constants.py` to reflect your local configuration.

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
rm views/user/password.html
```

#### Remove Svelte

Simply remove the `svelte` folder and the JS package files.

```bash
rm views/svelte.html
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
* Replace values for environment variables in `supervisord.conf`
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

Back end:

```bash
poetry shell
python main.py --debug=1
```

##### If Using Svelte

You also need to run another command for the front end in another terminal:

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

## Deploy to Production

### First Deploy Setup

Highly recommend you run something like [this harden script](https://github.com/bdoms/harden) to secure a new server.

There are some additional packages to install and configure in production:

```bash
sudo apt install nginx supervisor
```

#### Supervisor

Create user for supervisor - this is so we don't have to run as root:

```bash
sudo adduser --system --no-create-home --disabled-login --disabled-password --group supervisor
```

Make directories for the app:

```bash
sudo -u supervisor mkdir -p /srv/web
```

Create a sym link to the config.

```bash
sudo ln -s /srv/web/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
```

Start the supervisor daemon:

```bash
sudo service supervisor restart
```

#### Nginx

Create nginx user (nginx will fail to start without this):

```bash
sudo adduser --system --no-create-home --disabled-login --disabled-password --group nginx
```

Create symbolic links to conf files:

```bash
sudo mv /etc/nginx/nginx.conf /etc/nginx/nginx.old
sudo ln -s /srv/web/nginx.conf /etc/nginx/nginx.conf
```

Start the nginx server:

```bash
sudo service nginx restart
```

### Each Deploy

Copy the source code from the local machine (note that the trailing slash matters here).
Note that this method does not include package files.

You *could* include the `node_modules` and Python packages here if you want to.
However, that could increase transfer size and time significantly, so we choose not to.
The better alternative is to create limited access user for your repo and have them clone it.
For example, GitLab enables this with [deploy tokens](https://docs.gitlab.com/ee/user/project/deploy_tokens/).

```bash
rsync -avzhe ssh --progress --delete --exclude={.cache,.git,dist,node_modules,tests,__pycache__,*.pyc} trestle/ YOUR_USERNAME@IP_ADDRESS_OR_HOST:/srv/web
```

A deploy script is available to run all the relevant commands to build and restart the app at once.
Run it with:

```bash
./deploy.sh
```

Note that this is purposefully run without `sudo`, but you will be prompted to authenticate.

Logs are in `/var/log/supervisor/`.

You only need to restart nginx if its config has changed. Run this to pick up the changes:

```bash
sudo service nginx restart
```

#### Deploy with Svelte

Be sure to uncomment these two lines in `deploy.sh` if you're using Svelte, so the app gets synced and rebuilt:

```bash
yarn install
yarn build
```

You can fine tune builds with lots of options from [Parcel](https://parceljs.org/cli.html).

### Backup

Replace the defaults below with whatever you specified for your database connection above.

```bash
pg_dump -W -U trestle_user -F t trestle > trestle.tar
```

Transfer:

```bash
scp trestle.tar YOUR_USERNAME@IP_ADDRESS_OR_HOST:/srv/web/
```

And restore:

```bash
pg_restore -d trestle -U trestle_user trestle.tar
```
