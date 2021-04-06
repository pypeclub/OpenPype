---
id: admin_distribute
title: Distribute
sidebar_label: Distribute
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

To let your artists to use OpenPype, you'll need to distribute the frozen executables to them.

Distribution consists of two parts

 ### 1. OpenPype Igniter
 
 This is the base application that will be installed locally on each workstation.
 It is self contained (frozen) software that also includes all of the OpenPype codebase with the version
 from the time of the build.

 Igniter package is around 500MB and preparing an updated version requires you to re-build pype. That would be 
 inconvenient for regular and quick distribution of production updates and fixes. So you can distribute those
 independently, without requiring you artists to re-install every time.

 ### 2. OpenPype Codebase

When you upgrade your studio pype deployment to a new version or make any local code changes, you can distribute
these changes to your artists, without the need of re-building OpenPype, by using `create_zip` tool provided.
The resulting zip needs to be made available to the artists and it will override their local OpenPype install
with the updated version.

You have two ways of making this happen

#### Automatic Updates

Everytime and Artist launches OpenPype on their workstation, it will look to a pre-defined 
[openPype update location](#self) for any versions that are newer than the
latest, locally installed version. If such version is found, it will be downloaded,  
automatically extracted to the correct place and launched. This will become the default 
version to run for the artist, until a higher version is detected in the update location again.

#### Manual Updates

If for some reason you don't want to use the automatic updates, you can distribute your
zips manually. Your artist will then have to unpack them to the correct place on their disk.

The default locations are:

- Windows: `C:\Users\%USERNAME%\AppData\Local\pypeclub\openpype`
- Linux: `        `
- Mac: `        `
