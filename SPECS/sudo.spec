## START: Set by rpmautospec
## (rpmautospec version 0.6.5)
## RPMAUTOSPEC: autorelease, autochangelog
%define autorelease(e:s:pb:n) %{?-p:0.}%{lua:
    release_number = 4;
    base_release_number = tonumber(rpm.expand("%{?-b*}%{!?-b:1}"));
    print(release_number + base_release_number - 1);
}%{?-e:.%{-e*}}%{?-s:.%{-s*}}%{!?-n:%{?dist}}
## END: Set by rpmautospec

# comment out if no extra version
%global extraver p2

Summary: Allows restricted root access for specified users
Name: sudo
Version: 1.9.17
# Remove "-b 3" after rebase !!!
# use "-p -e %{?extraver}" when beta
# use "-e %{?extraver}" when patch version
# use nothing special when normal version
Release: %autorelease -e %{?extraver}.1
License: ISC
URL: https://www.sudo.ws
Source0: %{url}/dist/%{name}-%{version}%{?extraver}.tar.gz
Source1: sudoers
Source2: sudo-ldap.conf
Requires: pam
Requires: /usr/bin/vi

BuildRequires: make
BuildRequires: pam-devel
BuildRequires: groff
BuildRequires: openldap-devel
BuildRequires: flex
BuildRequires: bison
BuildRequires: libtool
BuildRequires: audit-libs-devel libcap-devel
BuildRequires: gettext
BuildRequires: zlib-devel


Patch1: 0001-coverity.patch
Patch2: 0002-sudo-conf.patch
Patch3: 0003-rebuild_env-Avoid-setting-SHELL-twice-for-sudo-i.patch
Patch4: 0004-cve-2026-35535.patch

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
        --with-editor=/usr/bin/vi \
        --with-env-editor \
        --with-ignore-dot \
        --with-tty-tickets \
        --with-ldap \
        --with-ldap-conf-file="%{_sysconfdir}/sudo-ldap.conf" \
        --without-selinux \
        --with-sendmail=/usr/sbin/sendmail \
        --with-passprompt="[sudo] password for %p: " \
        --disable-python \
        --enable-zlib=system \
        --with-linux-audit \
        --with-sssd
make

%check
make check

%install
rm -rf $RPM_BUILD_ROOT

# Update README.LDAP (#736653)
sed -i 's|/etc/ldap\.conf|%{_sysconfdir}/sudo-ldap.conf|g' README.LDAP.md

make install DESTDIR="$RPM_BUILD_ROOT" install_uid=`id -u` install_gid=`id -g` sudoers_uid=`id -u` sudoers_gid=`id -g`

chmod 755 $RPM_BUILD_ROOT%{_bindir}/* $RPM_BUILD_ROOT%{_sbindir}/*
install -p -d -m 700 $RPM_BUILD_ROOT/var/db/sudo
install -p -d -m 700 $RPM_BUILD_ROOT/var/db/sudo/lectured
install -p -d -m 750 $RPM_BUILD_ROOT/etc/sudoers.d
install -p -c -m 0440 %{SOURCE1} $RPM_BUILD_ROOT/etc/sudoers
install -p -c -m 0640 %{SOURCE2} $RPM_BUILD_ROOT/%{_sysconfdir}/sudo-ldap.conf

# create sudo-ldap.conf man
echo ".so man5/sudoers.ldap.5" > sudo-ldap.conf.5
gzip sudo-ldap.conf.5
install -p -c -m 0644 sudo-ldap.conf.5.gz $RPM_BUILD_ROOT/%{_mandir}/man5/sudo-ldap.conf.5.gz
rm -f sudo-ldap.conf.5.gz

#add sudo to protected packages
install -p -d -m 755 $RPM_BUILD_ROOT/etc/dnf/protected.d/
touch sudo.conf
echo sudo > sudo.conf
install -p -c -m 0644 sudo.conf $RPM_BUILD_ROOT/etc/dnf/protected.d/
rm -f sudo.conf

chmod +x $RPM_BUILD_ROOT%{_libexecdir}/sudo/*.so # for stripping, reset in %%files

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
%attr(0640,root,root) %config(noreplace) /etc/sudo.conf
%attr(0640,root,root) %config(noreplace) %{_sysconfdir}/sudo-ldap.conf
%attr(0750,root,root) %dir /etc/sudoers.d/
%config(noreplace) /etc/pam.d/sudo
%config(noreplace) /etc/pam.d/sudo-i
%attr(0644,root,root) %{_tmpfilesdir}/sudo.conf
%attr(0644,root,root) %config(noreplace) /etc/dnf/protected.d/sudo.conf
%dir /var/db/sudo
%dir /var/db/sudo/lectured
%attr(4111,root,root) %{_bindir}/sudo
%{_bindir}/sudoedit
%{_bindir}/cvtsudoers
%attr(0111,root,root) %{_bindir}/sudoreplay
%attr(0755,root,root) %{_sbindir}/visudo
%dir %{_libexecdir}/sudo
%attr(0644,root,root) %{_libexecdir}/sudo/sudo_noexec.so
%attr(0644,root,root) %{_libexecdir}/sudo/audit_json.so
%attr(0644,root,root) %{_libexecdir}/sudo/sudoers.so
%attr(0644,root,root) %{_libexecdir}/sudo/group_file.so
%attr(0644,root,root) %{_libexecdir}/sudo/system_group.so
%attr(0644,root,root) %{_libexecdir}/sudo/libsudo_util.so.?.?.?
%{_libexecdir}/sudo/libsudo_util.so.?
%{_libexecdir}/sudo/libsudo_util.so
%{_mandir}/man5/sudoers.5*
%{_mandir}/man5/sudoers.ldap.5*
%{_mandir}/man5/sudo-ldap.conf.5*
%{_mandir}/man5/sudo.conf.5*
%{_mandir}/man8/sudo.8*
%{_mandir}/man8/sudoedit.8*
%{_mandir}/man8/sudoreplay.8*
%{_mandir}/man8/visudo.8*
%{_mandir}/man1/cvtsudoers.1*
%{_mandir}/man5/sudoers_timestamp.5*
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
* Thu Jun 18 2026 Lucas RAVAGNIER <lucas.ravagnier@vates.tech> - 1.9.17-4.p2.1
- Rebase to sudo 1.9.17p2 el10
- Drop CVE-2025-32462 and CVE-2025-32463 (fixed in 1.9.17 upstream)
- Add rebuild_env fix for SHELL env variable with sudo -i
  *** XCP-ng changelog ***
	* Thu Aug 14 2025 Gaëtan Lehmann <gaetan.lehmann@vates.tech> - 1.9.15-5.1
	- Sync with 1.9.15-5
	- *** Upstream changelog ***
  	   * Tue Nov 12 2024 Lin Liu <Lin.Liu01@cloud.com> - 1.9.15-5
  	   - CP-50489: Remove selinux

	* Mon Aug 12 2024 Samuel Verschelde <stormi-xcp@ylix.fr> - 1.9.15-4.1
	- Sync with 1.9.15-4
	- *** Upstream changelog ***
	   - * Thu Jul 4 2024 Lin Liu <Lin.Liu01@cloud.com> - 1.9.15-4
	   - Drop python plugin as not required

	* Thu May 23 2024 Gael Duperrey <gduperrey@vates.tech> - 1.9.15-3.1
	- Synced from sudo-1.9.15-3.xs8.src.rpm
	- Removed XS-specific test of dist macro to determine buildrequires

	* Wed Mar 06 2024 Ross Lagerwall <ross.lagerwall@citrix.com> - 1.9.15-3
	- CA-389574: Depend on vi

	* Wed Feb 28 2024 Frediano Ziglio <frediano.ziglio@cloud.com> - 1.9.15-2
	- Bump release

	* Tue Feb 20 2024 Frediano Ziglio <frediano.ziglio@cloud.com> - 1.9.15-1
	- First imported release

## START: Generated by rpmautospec
* Fri Apr 10 2026 Alejandro López <allopez@redhat.com> - 1.9.17-4.p2
- Bump release number
- Resolves: RHEL-164620 - CVE-2026-35535 sudo: Sudo: Privilege escalation
  due to failure in privilege drop calls

* Tue Apr 07 2026 Alejandro López <allopez@redhat.com> - 1.9.17-3.p2
- Resolves: RHEL-164620 - CVE-2026-35535 sudo: Sudo: Privilege escalation
  due to failure in privilege drop calls

* Fri Nov 14 2025 Alejandro López <allopez@redhat.com> - 1.9.17-2.p2
- Resolves: RHEL-59136 - sudo passes SHELL environment variable twice to
  the shell being executed [rhel-10]
- Resolves: RHEL-128212 - [RFE] request to backport support for regex in
  sudo [rhel-10]
- Resolves: RHEL-112100 - Rebase of sudo to 1.9.17p2 [rhel-10]

* Fri Oct 24 2025 Alejandro López <allopez@redhat.com> - 1.9.17-1.p2
- Rebase sudo to 1.9.17p2
- Resolves: RHEL-122752

* Tue Jul 08 2025 Alejandro López <allopez@redhat.com> - 1.9.15-9.p5
- RHEL 10.1 ERRATUM
- CVE-2025-32462 sudo: LPE via host option Resolves: RHEL-100009
- CVE-2025-32463 sudo: LPE via chroot option Resolves: RHEL-100022

* Tue Oct 29 2024 Troy Dawson <tdawson@redhat.com> - 1.9.15-8.p5
- Bump release for October 2024 mass rebuild:

* Wed Aug 21 2024 Radovan Sroka <rsroka@redhat.com> - 1.9.15-7.p5
- RHEL 10.0 ERRATUM
- sudo-1.9.15-2.p5.el10: RHEL SAST Automation: address 4 High impact true
  positive(s) Resolves: RHEL-44436
- sudo subpackage sudo-logsrvd should not be built Resolves: RHEL-52864

* Mon Aug 19 2024 Radovan Sroka <rsroka@redhat.com> - 1.9.15-6.p5
- RHEL 10.0 ERRATUM
- sudo-1.9.15-2.p5.el10: RHEL SAST Automation: address 4 High impact true
  positive(s) Resolves: RHEL-44436
- sudo subpackage sudo-logsrvd should not be built Resolves: RHEL-52864

* Mon Aug 19 2024 Radovan Sroka <rsroka@redhat.com> - 1.9.15-5.p5
- RHEL 10.0 ERRATUM
- sudo-1.9.15-2.p5.el10: RHEL SAST Automation: address 4 High impact true
  positive(s) Resolves: RHEL-44436
- sudo subpackage sudo-logsrvd should not be built Resolves: RHEL-52864

* Mon Jun 24 2024 Troy Dawson <tdawson@redhat.com> - 1.9.15-4.p5
- Bump release for June 2024 mass rebuild

* Tue May 28 2024 koncpa <pkoncity@redhat.com> - 1.9.15-3.p5
- Enable RHEL gating for sudo

* Thu Feb 08 2024 Yaakov Selkowitz <yselkowi@redhat.com> - 1.9.15-2.p5
- Avoid sendmail build dependency

* Wed Jan 24 2024 Radovan Sroka <rsroka@redhat.com> - 1.9.15-1.p5
- Rabase to 1.9.15p5
- sudo-1_9_15p5 is available Resolves: rhbz#2248505
- TRIAGE CVE-2023-42465 sudo: Targeted Corruption of Register and Stack
  Variables Resolves: rhbz#2255569

* Tue Jul 25 2023 Yaakov Selkowitz <yselkowi@redhat.com> - 1.9.14-1.p3
- Rebase to 1.9.14p3
- sudo-1_9_14p2 is available Resolves: rhbz#2175672
- sudo fails to build with Python 3.12: FAILED: testcase
  check_example_group_plugin_is_able_to_debug() Resolves: rhbz#2186412

* Sat Jul 22 2023 Fedora Release Engineering <releng@fedoraproject.org> - 1.9.13-6.p2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_39_Mass_Rebuild

* Thu Jul 06 2023 Leigh Scott <leigh123linux@gmail.com> - 1.9.13-5.p2
- Rebuilt for Python 3.12

* Tue Jun 20 2023 Radovan Sroka <rsroka@redhat.com> - 1.9.13-4.p2
- migrated to SPDX license

* Tue Jun 13 2023 Python Maint <python-maint@redhat.com> - 1.9.13-3.p2
- Rebuilt for Python 3.12

* Wed Apr 26 2023 Florian Weimer <fweimer@redhat.com> - 1.9.13-2.p2
- Port configure script to C99

* Wed Mar 01 2023 Radovan Sroka <rsroka@redhat.com> - 1.9.13-1.p2
- Rebase to sudo 1.9.13p2
- sudo-1.9.13p2 is available Resolves: rhbz#2169840
- sudo: double free with per-command chroot sudoers rules Resolves:
  CVE-2023-27320

* Thu Jan 19 2023 Radovan Sroka <rsroka@redhat.com> - 1.9.12-1.p2
- Rebase to sudo 1.9.12p2
- sudo-1.9.12p2 is available Resolves: rhbz#2137775
- sudo: arbitrary file write with privileges of the RunAs user Resolves:
  CVE-2023-22809

* Sat Jul 23 2022 Fedora Release Engineering <releng@fedoraproject.org> - 1.9.11-4.p3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_37_Mass_Rebuild

* Wed Jun 22 2022 Radovan Sroka <rsroka@redhat.com> - 1.9.11-3.p3
- Update to 1.9.11p3

* Mon Jun 13 2022 Python Maint <python-maint@redhat.com> - 1.9.8-7.p2
- Rebuilt for Python 3.11

* Mon Jun 06 2022 Matthew Miller <mattdm@mattdm.org> - 1.9.8-6.p2
- recommend system-default-editor instead of nano specifically

* Sat Jan 22 2022 Fedora Release Engineering <releng@fedoraproject.org> - 1.9.8-5.p2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_36_Mass_Rebuild

* Wed Oct 06 2021 Radovan Sroka <rsroka@redhat.com> - 1.9.8-4.p2
- Rebuild. previously built with wrong version

* Wed Oct 06 2021 Radovan Sroka <rsroka@redhat.com> - 1.9.8-3
- Set up update workflow with %%autorelease macro
- removed stri patch that was not relevant

* Sun Oct 03 2021 Matthew Miller <mattdm@mattdm.org> - 1.9.8p2-2
- rhbz#1328973 -- make nano the default with fallback to vim and vi in that
  order

* Sun Oct 03 2021 Matthew Miller <mattdm@mattdm.org> - 1.9.8p2-1
- Update to 1.9.8p2, and include new sudo_intercept.so

* Tue Sep 14 2021 Sahana Prasad <sahana@redhat.com> - 1.9.7p2-5
- Rebuilt with OpenSSL 3.0.0

* Sat Aug  7 2021 Matthew Miller <mattdm@fedoraproject.org> - 1.9.7p2-2
- drop obsolete requirement for post script that doesn't exist anymore
  (thanks @scfc)
- remove commented-out lines from prior PR

* Fri Jul 30 2021 Peter Czanik <peter@czanik.hu> - 1.9.7p2-1
- update to 1.9.7p2
- follow up path change in strip patch
- added --enable-zlib=system configure parameter, so sudo uses system zlib,
  autoconf is no more needed

* Fri Jul 23 2021 Fedora Release Engineering <releng@fedoraproject.org> - 1.9.5p2-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_35_Mass_Rebuild

* Fri Jun 04 2021 Python Maint <python-maint@redhat.com> - 1.9.5p2-2
- Rebuilt for Python 3.10

* Tue Jan 26 2021 Matthew Miller <mattdm@fedoraproject.org> - 1.9.5p2-1
- rebase to 1.9.5p2
Resolves: rhbz#1920611
- fixed CVE-2021-3156 sudo: Heap buffer overflow in argument parsing
Resolves: rhbz#1920618

* Mon Jan 18 2021 Radovan Sroka <rsroka@redhat.com> - 1.9.5p1-1
- rebase to 1.9.5p1
Resolves: rhbz#1902758
- fixed double free in sss_to_sudoers
Resolves: rhbz#1885874
- fixed CVE-2021-23239 sudo: possible directory existence test due to race condition in sudoedit
Resolves: rhbz#1915055
- fixed CVE-2021-23240 sudo: symbolic link attack in SELinux-enabled sudoedit
Resolves: rhbz#1915054

* Wed Jan 13 2021 Jonathan Lebon <jonathan@jlebon.com> - 1.9.3p1-2
- split out Python modules into separate subpackage
Resolves: rhbz#1909299

* Mon Oct 05 2020 Radovan Sroka <rsroka@redhat.com> - 1.9.3p1-1
- rebase to 1.9.3p1
- enable python modules
Resolves: rhbz#1881112

* Tue Sep 15 2020 Radovan Sroka <rsroka@redhat.com> - 1.9.2-1
- rebase to 1.9.2
Resolves: rhbz#1859577
- added logsrvd subpackage
- added openssl-devel buildrequires
Resolves: rhbz#1860653
- fixed sudo runstatedir path
Resolves: rhbz#1868215
- added /var/lib/snapd/snap/bin to secure_path variable
Resolves: rhbz#1691996

* Sat Aug 01 2020 Fedora Release Engineering <releng@fedoraproject.org> - 1.9.1-3
- Second attempt - Rebuilt for
  https://fedoraproject.org/wiki/Fedora_33_Mass_Rebuild

* Wed Jul 29 2020 Fedora Release Engineering <releng@fedoraproject.org> - 1.9.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_33_Mass_Rebuild

* Wed Jul 08 2020 Attila Lakatos <alakatos@redhat.com> - 1.9.1-1
- rebase to 1.9.1
Resolves: rhbz#1848788
- fix rpmlint errors
Resolves: rhbz#1817139

* Wed Mar 25 2020 Attila Lakatos <alakatos@redhat.com> - 1.9.0-0.1.b4
- update to latest development version 1.9.0b4
Resolves: rhbz#1816593

* Mon Feb 24 2020 Attila Lakatos <alakatos@redhat.com> - 1.9.0-0.1.b1
- update to latest development version 1.9.0b1
- added sudo_logsrvd and sudo_sendlog to files and their appropriate man pages
Resolves: rhbz#1787823
- Stack based buffer overflow in when pwfeedback is enabled
Resolves: rhbz#1796945
- fixes: CVE-2019-18634
- By using ! character in the shadow file instead of a password hash can access to a run as all sudoer account
Resolves: rhbz#1786709
- fixes CVE-2019-19234
- attacker with access to a Runas ALL sudoer account can impersonate a nonexistent user
Resolves: rhbz#1786705
- fixes CVE-2019-19232

* Fri Jan 31 2020 Fedora Release Engineering <releng@fedoraproject.org> - 1.8.29-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_32_Mass_Rebuild

* Mon Nov 11 2019 Radovan Sroka <rsroka@redhat.com> - 1.8.29-1
- rebase to 1.8.29
Resolves: rhbz#1766233

* Tue Oct 22 2019 Radovan Sroka <rsroka@redhat.com> - 1.8.28p1-1
- rebase to 1.8.28p1
Resolves: rhbz#1762350

* Tue Oct 15 2019 Radovan Sroka <rsroka@redhat.com> - 1.8.28-1
- rebase to 1.8.28
Resolves: rhbz#1761533
- set always_set_home by default
Resolves: rhbz#1728687
- Sync sudoers options from rhel8 to fedora
Resolves: rhbz#1761781
- CVE-2019-14287
Resolves: rhbz#1761584

* Sat Jul 27 2019 Fedora Release Engineering <releng@fedoraproject.org> - 1.8.27-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_31_Mass_Rebuild

* Sun Mar 31 2019 Marek Tamaskovic <mtamasko@redhat.com> 1.8.27-2
- resolves rhbz#1676925
- Removed PS1, PS2 from sudoers

* Mon Mar 11 2019 Radovan Sroka <rsroka@redhat.com> 1.8.27-1
- rebase sudo to 1.8.27

* Sun Feb 03 2019 Fedora Release Engineering <releng@fedoraproject.org> - 1.8.25p1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_30_Mass_Rebuild

* Mon Oct 01 2018 Radovan Sroka <rsroka@redhat.com> 1.8.25p1-1
- rebase sudo to 1.8.25p1

* Mon Sep 10 2018 Radovan Sroka <rsroka@redhat.com> 1.8.25-1
- rebase sudo to latest stawble version
- install /etc/dnf/protected.d/sudo instead of /etc/yum/protected.d/sudo (1626968)

* Sat Jul 14 2018 Fedora Release Engineering <releng@fedoraproject.org> - 1.8.23-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_29_Mass_Rebuild

* Tue Jul 03 2018 Matthew Miller <mattdm@fedoraproject.org> - 1.8.23-2
- remove defattr, as default is now sane

* Wed May 09 2018 Daniel Kopecek <dkopecek@redhat.com> - 1.8.23-1
- update to 1.8.23

* Wed Apr 18 2018 Daniel Kopecek <dkopecek@redhat.com> - 1.8.23-0.1.b3
- update to 1.8.23b3

* Fri Feb 09 2018 Fedora Release Engineering <releng@fedoraproject.org> - 1.8.22-0.2.b1
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Thu Dec 14 2017 Radovan Sroka <rsroka@redhat.com> - 1.8.22b1-1
- update to 1.8.22b1
- Added /usr/local/sbin and /usr/local/bin to secure path rhbz#1166185

* Thu Sep 21 2017 Marek Tamaskovic <mtamasko@redhat.com> - 1.8.21p2-1
- update to 1.8.21p2
- Moved libsudo_util.so from the -devel sub-package to main package (1481225)

* Wed Sep 06 2017 Matthew Miller <mattdm@fedoraproject.org> - 1.8.20p2-4
- replace file-based requirements with package-level ones

* Thu Aug 03 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.8.20p2-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.8.20p2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Thu Jun 01 2017 Daniel Kopecek <dkopecek@redhat.com> 1.8.20p2-1
- update to 1.8.20p2

* Wed May 31 2017 Daniel Kopecek <dkopecek@redhat.com> 1.8.20p1-1
- update to 1.8.20p1
- fixes CVE-2017-1000367
  Resolves: rhbz#1456884

* Fri Apr 07 2017 Jiri Vymazal <jvymazal@redhat.com> - 1.8.20-0.1.b1
- update to latest development version 1.8.20b1
- added sudo to dnf/yum protected packages
  Resolves: rhbz#1418756

* Mon Feb 13 2017 Tomas Sykora <tosykora@redhat.com> - 1.8.19p2-1
- update to 1.8.19p2

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.8.19-0.3.20161108git738c3cb
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Tue Nov 08 2016 Daniel Kopecek <dkopecek@redhat.com> 1.8.19-0.2.20161108git738c3cb
- update to latest development version
- fixes CVE-2016-7076

* Fri Sep 23 2016 Radovan Sroka <rsroka@redhat.com> 1.8.19-0.1.20160923git90e4538
- we were not able to update from rc and beta versions to stable one
- so this is a new snapshot package which resolves it

* Wed Sep 21 2016 Radovan Sroka <rsroka@redhat.com> 1.8.18-1
- update to 1.8.18

* Fri Sep 16 2016 Radovan Sroka <rsroka@redhat.com> 1.8.18rc4-1
- update to 1.8.18rc4

* Wed Sep 14 2016 Radovan Sroka <rsroka@redhat.com> 1.8.18rc2-1
- update to 1.8.18rc2
- dropped sudo-1.8.14p1-ldapconfpatch.patch

* Fri Aug 26 2016 Radovan Sroka <rsroka@redhat.com> 1.8.18b2-1
- update to 1.8.18b2
- added --disable-root-mailer as configure option
  Resolves: rhbz#1324091

* Fri Jun 24 2016 Daniel Kopecek <dkopecek@redhat.com> 1.8.17p1-1
- update to 1.8.17p1
- install the /var/db/sudo/lectured
  Resolves: rhbz#1321414

* Tue May 31 2016 Daniel Kopecek <dkopecek@redhat.com> 1.8.16-4
- removed INPUTRC from env_keep to prevent a possible info leak
  Resolves: rhbz#1340701

* Mon Apr 04 2016 Daniel Kopecek <dkopecek@redhat.com> 1.8.16-1
- update to 1.8.16

* Thu Nov  5 2015 Daniel Kopecek <dkopecek@redhat.com> 1.8.15-1
- update to 1.8.15
- fixes CVE-2015-5602

* Mon Aug 24 2015 Radovan Sroka <rsroka@redhat.com> 1.8.14p3-3
- enable upstream test suite

* Mon Jul 27 2015 Radovan Sroka <rsroka@redhat.com> 1.8.14p3-1
- update to 1.8.14p3

* Mon Jul 20 2015 Radovan Sroka <rsroka@redhat.com> 1.8.14p1-1
- update to 1.8.14p1-1

* Fri Jul 10 2015 Radovan Sroka <rsroka@redhat.com> - 1.8.14b4-1
- Update to 1.8.14b4
- Add own %%{_tmpfilesdir}/sudo.conf

* Fri Jun 19 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.8.12-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Wed Feb 18 2015 Daniel Kopecek <dkopecek@redhat.com> - 1.8.12
- update to 1.8.12
- fixes CVE-2014-9680

* Mon Nov  3 2014 Daniel Kopecek <dkopecek@redhat.com> - 1.8.11p2-1
- update to 1.8.11p2

* Tue Sep 30 2014 Daniel Kopecek <dkopecek@redhat.com> - 1.8.11-1
- update to 1.8.11

* Tue Aug  5 2014 Tom Callaway <spot@fedoraproject.org> - 1.8.8-6
- fix license handling

* Mon Sep 30 2013 Daniel Kopecek <dkopecek@redhat.com> - 1.8.8-1
- update to 1.8.8

* Thu Feb 28 2013 Daniel Kopecek <dkopecek@redhat.com> - 1.8.6p7-1
- update to 1.8.6p7
- fixes CVE-2013-1775 and CVE-2013-1776

* Mon Nov 12 2012 Daniel Kopecek <dkopecek@redhat.com> - 1.8.6p3-2
- added upstream patch for a regression

* Tue Sep 25 2012 Daniel Kopecek <dkopecek@redhat.com> - 1.8.6p3-1
- update to 1.8.6p3

* Thu May 17 2012 Daniel Kopecek <dkopecek@redhat.com> - 1.8.5-1
- update to 1.8.5
- fixed CVE-2012-2337

* Thu Jan 26 2012 Daniel Kopecek <dkopecek@redhat.com> - 1.8.3p1-3
- added patch for CVE-2012-0809

* Thu Nov 10 2011 Daniel Kopecek <dkopecek@redhat.com> - 1.8.3p1-1
- update to 1.8.3p1

* Tue Jul 12 2011 Daniel Kopecek <dkopecek@redhat.com> - 1.8.1p2-1
- rebase to 1.8.1p2

* Mon Jan 17 2011 Daniel Kopecek <dkopecek@redhat.com> - 1.7.4p5-2
- rebase to 1.7.4p5
- fixes CVE-2011-0008, CVE-2011-0010

* Tue Nov 30 2010 Daniel Kopecek <dkopecek@redhat.com> - 1.7.4p4-5
- anybody in the wheel group has now root access (using password)

* Thu Aug 20 2009 Daniel Kopecek <dkopecek@redhat.com> 1.7.1-6
- moved secure_path from compile-time option to sudoers file

* Mon Jun 22 2009 Daniel Kopecek <dkopecek@redhat.com> 1.7.1-1
- updated sudo to version 1.7.1

* Tue Feb 24 2009 Daniel Kopecek <dkopecek@redhat.com> 1.6.9p17-6
- fixed building with new libtool
- added /usr/local/sbin to secure-path

* Tue Jan 13 2009 Daniel Kopecek <dkopecek@redhat.com> 1.6.9p17-3
- Added /usr/local/bin to secure-path
## END: Generated by rpmautospec
