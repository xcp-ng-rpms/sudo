%global package_speccommit a084333d62adee9514dde8b914ec1409910bce5a
%global usver 1.9.15
%global xsver 2
%global xsrel %{xsver}%{?xscount}%{?xshash}

# comment out if no extra version
%global extraver p5

Summary: Allows restricted root access for specified users
Name: sudo
Version: 1.9.15
# remove -b 3 after rebase !!!
# use "-p -e % {?extraver}" when beta
# use "-e % {?extraver}"" when patch version
# use nothing special when normal version
Release: %{?xsrel}.1%{?dist}
License: ISC
URL: https://www.sudo.ws
Source0: sudo-1.9.15p5.tar.gz
Source1: sudoers
Requires: pam

BuildRequires: make
BuildRequires: pam-devel
BuildRequires: groff
BuildRequires: openldap-devel
BuildRequires: flex
BuildRequires: bison
BuildRequires: libtool
BuildRequires: audit-libs-devel libcap-devel
BuildRequires: libselinux-devel
BuildRequires: gettext
BuildRequires: zlib-devel

%description
Sudo (superuser do) allows a system administrator to give certain
users (or groups of users) the ability to run some (or all) commands
as root while logging all commands and arguments. Sudo operates on a
per-command basis.  It is not a replacement for the shell.  Features
include: the ability to restrict what commands a user may run on a
per-host basis, copious logging of each command (providing a clear
audit trail of who did what), a configurable timeout of the sudo
command, and the ability to use the same configuration file (sudoers)
on many different machines.

%package        devel
Summary:        Development files for %{name}
Requires:       %{name} = %{version}-%{release}

%description    devel
The %{name}-devel package contains header files developing sudo
plugins that use %{name}.


%package        logsrvd
Summary:        High-performance log server for %{name}
Requires:       %{name} = %{version}-%{release}
BuildRequires:  openssl-devel


%description    logsrvd
%{name}-logsrvd is a high-performance log server that accepts event and I/O logs from sudo.
It can be used to implement centralized logging of sudo logs.

%prep
%autosetup -p1 -n %{name}-%{version}%{?extraver}

%build
# Remove bundled copy of zlib
rm -rf zlib/

%ifarch s390 s390x sparc64
F_PIE=-fPIE
%else
F_PIE=-fpie
%endif

export CFLAGS="$RPM_OPT_FLAGS $F_PIE" LDFLAGS="-pie -Wl,-z,relro -Wl,-z,now"

%configure \
        --prefix=%{_prefix} \
        --sbindir=%{_sbindir} \
        --libdir=%{_libdir} \
        --docdir=%{_pkgdocdir} \
        --enable-tmpfiles.d=%{_tmpfilesdir} \
        --enable-openssl \
        --disable-root-mailer \
        --disable-intercept \
        --with-logging=syslog \
        --with-logfac=authpriv \
        --with-pam \
        --with-pam-login \
        --with-editor=%{_bindir}/nano:%{_bindir}/vim:%{_bindir}/vi \
        --with-env-editor \
        --with-ignore-dot \
        --with-tty-tickets \
        --with-ldap \
        --with-selinux \
        --with-sendmail=/usr/sbin/sendmail \
        --with-passprompt="[sudo] password for %p: " \
        --enable-zlib=system \
        --with-linux-audit \
        --with-sssd
#       --without-kerb5 \
#       --without-kerb4
make

%check
make check

%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR="$RPM_BUILD_ROOT" install_uid=`id -u` install_gid=`id -g` sudoers_uid=`id -u` sudoers_gid=`id -g`

chmod 755 $RPM_BUILD_ROOT%{_bindir}/* $RPM_BUILD_ROOT%{_sbindir}/*
install -p -d -m 700 $RPM_BUILD_ROOT/var/db/sudo
install -p -d -m 700 $RPM_BUILD_ROOT/var/db/sudo/lectured
install -p -d -m 750 $RPM_BUILD_ROOT/etc/sudoers.d
install -p -c -m 0440 %{SOURCE1} $RPM_BUILD_ROOT/etc/sudoers
#add sudo to protected packages
%if 0%{?xenserver} > 8
install -p -d -m 755 $RPM_BUILD_ROOT/etc/dnf/protected.d/
touch sudo.conf
echo sudo > sudo.conf
install -p -c -m 0644 sudo.conf $RPM_BUILD_ROOT/etc/dnf/protected.d/
rm -f sudo.conf
%endif

chmod +x $RPM_BUILD_ROOT%{_libexecdir}/sudo/*.so # for stripping, reset in %%files

# Don't package LICENSE as a doc
rm -rf $RPM_BUILD_ROOT%{_pkgdocdir}/LICENSE

# Remove examples; Examples can be found in man pages too.
rm -rf $RPM_BUILD_ROOT%{_datadir}/examples
rm -rf $RPM_BUILD_ROOT%{_pkgdocdir}/examples

#Remove all .la files
find $RPM_BUILD_ROOT -name '*.la' -exec rm -f {} ';'

# Remove sudoers.dist
rm -f $RPM_BUILD_ROOT%{_sysconfdir}/sudoers.dist

%find_lang sudo
%find_lang sudoers

cat sudo.lang sudoers.lang > sudo_all.lang
rm sudo.lang sudoers.lang

mkdir -p $RPM_BUILD_ROOT/etc/pam.d
cat > $RPM_BUILD_ROOT/etc/pam.d/sudo << EOF
#%%PAM-1.0
auth       include      system-auth
account    include      system-auth
password   include      system-auth
session    optional     pam_keyinit.so revoke
session    required     pam_limits.so
session    include      system-auth
EOF

cat > $RPM_BUILD_ROOT/etc/pam.d/sudo-i << EOF
#%%PAM-1.0
auth       include      sudo
account    include      sudo
password   include      sudo
session    optional     pam_keyinit.so force revoke
session    include      sudo
EOF


%files -f sudo_all.lang
%defattr(-,root,root)
%attr(0440,root,root) %config(noreplace) /etc/sudoers
%attr(0750,root,root) %dir /etc/sudoers.d/
%config(noreplace) /etc/pam.d/sudo
%config(noreplace) /etc/pam.d/sudo-i
%attr(0644,root,root) %{_tmpfilesdir}/sudo.conf
%if 0%{?xenserver} > 8
%attr(0644,root,root) %config(noreplace) /etc/dnf/protected.d/sudo.conf
%endif
%attr(0640,root,root) %config(noreplace) /etc/sudo.conf
%dir /var/db/sudo
%dir /var/db/sudo/lectured
%attr(4111,root,root) %{_bindir}/sudo
%{_bindir}/sudoedit
%attr(0111,root,root) %{_bindir}/sudoreplay
%attr(0755,root,root) %{_sbindir}/visudo
%{_bindir}/cvtsudoers
%dir %{_libexecdir}/sudo
%attr(0755,root,root) %{_libexecdir}/sudo/sesh
%attr(0644,root,root) %{_libexecdir}/sudo/sudo_noexec.so
%attr(0644,root,root) %{_libexecdir}/sudo/sudoers.so
%attr(0644,root,root) %{_libexecdir}/sudo/audit_json.so
%attr(0644,root,root) %{_libexecdir}/sudo/group_file.so
%attr(0644,root,root) %{_libexecdir}/sudo/system_group.so
%attr(0644,root,root) %{_libexecdir}/sudo/libsudo_util.so.?.?.?
%{_libexecdir}/sudo/libsudo_util.so.?
%{_libexecdir}/sudo/libsudo_util.so
%{_mandir}/man5/sudoers.5*
%{_mandir}/man5/sudoers.ldap.5*
%{_mandir}/man5/sudo.conf.5*
%{_mandir}/man8/sudo.8*
%{_mandir}/man8/sudoedit.8*
%{_mandir}/man8/sudoreplay.8*
%{_mandir}/man8/visudo.8*
%{_mandir}/man1/cvtsudoers.1.gz
%{_mandir}/man5/sudoers_timestamp.5.gz
%dir %{_pkgdocdir}/
%{_pkgdocdir}/*
%{!?_licensedir:%global license %%doc}
%license LICENSE.md
%exclude %{_pkgdocdir}/ChangeLog

%files devel
%doc plugins/sample/sample_plugin.c
%{_includedir}/sudo_plugin.h
%{_mandir}/man5/sudo_plugin.5*

%files logsrvd
%attr(0640,root,root) %config(noreplace) /etc/sudo_logsrvd.conf
%attr(0755,root,root) %{_sbindir}/sudo_logsrvd
%attr(0755,root,root) %{_sbindir}/sudo_sendlog
%{_mandir}/man5/sudo_logsrv.proto.5.gz
%{_mandir}/man5/sudo_logsrvd.conf.5.gz
%{_mandir}/man8/sudo_logsrvd.8.gz
%{_mandir}/man8/sudo_sendlog.8.gz

%changelog
* Tue May 21 2024 Gael Duperrey <gduperrey@vates.tech> - 1.9.15-2.1
- Synced from XS82ECU1063
- Removed XS-specific test of dist macro to determine buildrequires

* Wed Feb 28 2024 Frediano Ziglio <frediano.ziglio@cloud.com> - 1.9.15-2
- Bump release

* Tue Feb 20 2024 Frediano Ziglio <frediano.ziglio@cloud.com> - 1.9.15-1
- First imported release

