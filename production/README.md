Production Configuration
========================

If you want to get a production server of OCTAL started quickly, skip ahead to the Amazon EC2 section.

Whereas the [README](/README.md) describes insructions for setting up a development server with OCTAL, the following instructions are intended to bring up an OCTAL server into production.

The following instructions run OCTAL using the Gunicorn Python WSGI HTTP server and Nginx for static file serving on a Fedora platform.

## Amazon EC2

OCTAL 2.0 has been bundled as an Amazon EC2 AMI which will allow you to start a server with OCTAL pre-configured in production.
The following snapshot is from the [v2.0-ms branch](https://github.com/danallan/octal-application/tree/v2.0-ms) on a Fedora installation with Gunicorn and Nginx.

[Click here to launch an instance based on the AMI](https://console.aws.amazon.com/ec2/v2/home?region=us-west-2#LaunchInstanceWizard:ami=ami-df3746ef)

We recommend an m1.small instance, unless you know you need more power.
The image, ami-df3746ef, is available in the EC2 US West (Oregon) region.

## From Scratch

The following steps should bring an OCTAL production server up from scratch.

1. Fire up a SMALL instance of [Fedora](http://fedoraproject.org/en_GB/get-fedora#clouds) on Amazon EC2.

1. SSH in (Fedora 19 and later require username of 'fedora' during SSH)

1. Initial package install:

        sudo su
        yum -y update
        yum -y upgrade
        yum -y install screen freetype-devel gcc gcc-gfortran git wget vim nodejs npm python-devel make numpy numpy-f2py scipy python-matplotlib libpng-devel
        easy_install virtualenv nginx supervisor

1. Install PIP:

        wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py
        python get-pip.py
        rm get-pip.py

1. Add octal user and make directory structure:

        adduser octal
        mkdir /srv/octal /srv/log
        chown -R octal:octal /srv/
        chown -R octal:octal /var/lib/nginx/
        su octal

1. Fetch the OCTAL code and build the dependencies:

        cd /srv/octal
        git clone https://github.com/danallan/octal-application.git
        cd octal-application
        make

1. Dependency building will probably fail due to Numpy, Matplotlib, or Scipy packages. 
Skip this step if `make` did not fail.
If it did fail, do this to fix:

        rm -rf ../meta_venv

    1. Remove lines involving numpy, matplotlib, and pymc from requirements.txt
    1. Re-run `make`
    1. If successful, link numpy to the virtual environment:

            ln -s /usr/lib64/python2.7/site-packages/numpy /srv/octal/meta_venv/lib/python2.7/site-packages/

    1. Activate the virtual environment and build pymc

            source ../meta_venv/bin/activate
            pip install matplotlib pymc

1. Finish up the install by linking Scipy:

        ln -s /usr/lib64/python2.7/site-packages/scipy /srv/octal/meta_venv/lib/python2.7/site-packages/

1. Activate the virtual environment (if is not already)

        source ../meta_venv/bin/activate

1. Install gunicorn and uwsgi

        pip install gunicorn uwsgi

1. Prep log directory

        mkdir /var/log/django
        chown octal:octal /var/log/django

1. Continue the directions for your appropriate version, below.

### For [v1.1-pilot+postsurvey](https://github.com/danallan/octal-application/tree/v1.1-pilot+postsurvey) installations only

Skip to the next section if you're running a newer version.
The directions for this early version may be slightly outdated.
If you have problems, try some of the steps from a newer version.

1. Import the valid participant IDs into the db:

        app_server/manage.py dbshell
        (copy-patse contents of sqlite.txt into the sqlite shell)
        .quit

1. Build the exercise DB at the following URL:

        http://url-to-server:8080/octal/build_exercise_db


1. Add the following files:

        run_{app,content}_server.sh to /srv/
        nginx.conf to /etc/nginx/
        octal_{app,content}.ini to /etc/supervisord.d/

1. turn off stupid selinux (below) then restart

        SELINUX=disabled in /etc/selinux/config
        shutdown -r now

1. enable supervisor and nginx

        chkconfig nginx on
        chkconfig supervisord on

1. start supervisor

        supervisorctl reread
        supervisorctl update

1. start nginx

        service nginx start


### For [v2.0-ms](https://github.com/danallan/octal-application/tree/v2.0-ms) installations only

1. Update `octal-application/config.py`:

        META_TOP_LEVEL = path.realpath('/srv/octal/') #explicit path
        LOG_PATH = path.realpath('/srv/log') #explicit path
        DEBUG = False #change debug mode

1. Add the following to octal-application/server/settings.py (referencing instead the hosts and IPs applicable to your own application):

        ALLOWED_HOSTS = ['.domain.tld', 'host.amazonaws.com', '123.123.123.123']

1. Update `SECRET_KEY` in `octal-application/server/local_settings.py`

1. Add the following files:

        run_octal_server.sh to /srv/
        nginx.conf to /etc/nginx/
        octal.ini to /etc/supervisord.d/

1. turn off stupid selinux (below) then restart

        SELINUX=disabled in /etc/selinux/config
        shutdown -r now

1. enable supervisor and nginx

        chkconfig nginx on
        chkconfig supervisord on

1. start supervisor

        supervisorctl reread
        supervisorctl update

1. start nginx

        service nginx start
