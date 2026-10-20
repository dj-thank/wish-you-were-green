# Independent audit of three PEWDD identity conflicts

**Checked 18 October 2026 UTC.** This audit concerns only the immutable
PEWDD snapshot at
[`023dba3176ac367c6cf2b5968847a80d79e3c594`](https://github.com/jamietwilliams/PEWDD/blob/023dba3176ac367c6cf2b5968847a80d79e3c594/PEWDD.csv).

**The name–coordinate conflicts are present in the upstream CSV itself.**
Independent original-paper and Gaia checks establish two examples in which
the stellar name and atmosphere measurements are attached to another star's
Gaia ID, and a third example in which the Gaia ID is correct but the tabulated
coordinates disagree. The full flag list must therefore be called an
*identity-review list*, not a list of 233 proven incorrect Gaia IDs.

No upstream issue, message, or catalogue correction was submitted. The cause
of the conflicts and their full extent across fields have not been diagnosed.

## Inputs and independent parsing

The [official raw CSV](https://raw.githubusercontent.com/jamietwilliams/PEWDD/023dba3176ac367c6cf2b5968847a80d79e3c594/PEWDD.csv)
was downloaded again rather than trusting the previous parser's result.
Its 1,594,728 bytes have SHA256
`ed65260aa5b130198468ae8e482794868119f7f0e754cd53fbb5dd7d8baf83d3`,
exactly matching the already frozen local snapshot.

A separate `csv.reader` pass found 206 fields in the header and in **every one
of the 3,475 data rows**. Direct header-position access reproduces the names,
RA, Dec and Gaia designations below. This rules out a local comma/quoting or
column-shift explanation for these rows.

An independent Astropy sexagesimal-coordinate parser and spherical
separation calculation reproduce precisely the same **236 rows with a full
J-coordinate name more than 600 arcseconds from their tabulated position**.
Those rows mention 233 distinct Gaia designations. This reproduces the flag
count, not the number of wrong Gaia associations.

[PEWDD's usage documentation](https://pewdd-tutorial.readthedocs.io/en/latest/usage.html)
explains that `Identifier` specifies an object/paper entry and recommends
`Gaia_designation` for retrieving a star across multiple papers. The key
conflicts therefore matter when associating chemical measurements by Gaia
ID, even when the quantities attached to the original name were transcribed
correctly.

All exact query text, source URLs, file hashes, selected raw source records
and separations are in
[outputs/independent_key_audit.json](outputs/independent_key_audit.json).
The compact original ESA response is retained as
[sources/independent_gaia_identity.csv](sources/independent_gaia_identity.csv).
The Gaia query covers the three assigned IDs plus 30-arcsecond cones around
the three name-encoded positions. Source IDs are retained as strings.

## Case 1: a Koester measurement assigned to another Gaia star

**PEWDD data row 620**, index field 619:

- Name: `SDSS J000106.22+250330.0`.
- Paper: Koester 2015.
- Tabulated position: RA 157.032703345525°, Dec −1.5979708039908°.
- Assigned ID: `Gaia DR3 3782563919332193792`.
- Recorded effective temperature: 15,194 ± 75 K; log(H/He) −4.73 and
  log(Ca/He) −7.37.

The authors' [CDS table 1](https://cdsarc.cds.unistra.fr/ftp/J/A+A/583/A86/table1.dat),
data row 2, gives `000106.22+250330.00` with exactly those temperature,
hydrogen and calcium values. Its name encodes approximately RA 0.275917°,
Dec +25.058333°. The [table description](https://cdsarc.cds.unistra.fr/ftp/J/A+A/583/A86/ReadMe)
identifies this column as the SDSS name. Thus the name/measurement part of the
PEWDD entry can be traced to the original paper.

ESA Gaia DR3 places the assigned ID at RA **157.032563429°**, Dec
**−1.598080528°**, approximately **147.55 degrees** from the name-encoded
position. Independently, Coutu et al.'s
[table 1](https://cdsarc.cds.unistra.fr/ftp/J/ApJ/885/74/table1.dat), data row
505, identifies this same numeric ID with `2QZ J102807.8-013553`.
Koester's own table contains the corresponding `102807.83-013552.94` as a
separate object in row 386, with 13,617 ± 79 K and log(Ca/He) −8.49.

The ID and measurements therefore refer to different stars. A Gaia source,
`2853069985013789824`, lies **0.126 arcseconds** from the intended SDSS
name-encoded position. That is a strong positional replacement candidate;
this audit does not automatically replace the upstream association or claim
a fully adjudicated replacement crossmatch.

## Case 2: a Kepler measurement assigned to another Gaia star

**PEWDD data row 624**, index field 623:

- Name: `SDSS J000215.65+320914.12`.
- Paper: Kepler 2016.
- Tabulated position: RA 352.726158915891°, Dec +28.088213309298°.
- Assigned ID: `Gaia DR3 2865936671944556160`.
- Recorded effective temperature: 7,587 ± 110 K; log(Ca/He) −8.26.

The original [CDS table 6](https://cdsarc.cds.unistra.fr/ftp/J/MNRAS/455/3413/table6.dat.gz),
data row 5,991, gives the intended name and the same temperature and calcium
abundance, with spectrum `7127-56566-0528`. Its
[description](https://cdsarc.cds.unistra.fr/ftp/J/MNRAS/455/3413/ReadMe)
identifies the SDSS coordinate name and defines the calcium abundance in the
comment column.

The assigned Gaia source is instead at RA **352.726389742°**, Dec
**+28.088142158°**, about **7.90 degrees** from the intended name. Coutu's
original table 1, row 1,303, identifies this ID with
`SDSS J233054.31+280517.4`. Kepler's original table 6 also contains that other
object separately, in row 3,730, with spectrum `6514-56487-0489`, 7,198 ±
93 K and log(Ca/He) −8.53.

For the intended name, Coutu's table 1 row 3 instead records numeric Gaia ID
**`2873769975034246272`**. ESA Gaia DR3 independently returns this source
**0.436 arcseconds** from the name-encoded position. The original
identification and current Gaia position agree on this alternative. No
upstream row was changed.

## Case 3: a correct Gaia ID with conflicting coordinate fields

**PEWDD data row 645**, index field 644:

- Name: `SDSS J001557.38+183034.6`.
- Paper: Coutu 2019.
- Tabulated position: RA 14.58912°, Dec +11.043892°.
- Assigned ID: `Gaia DR3 2797320927258478464`.
- Recorded effective temperature: 7,346 ± 417 K; log(H/He) −4.07.

Coutu's [original table 1](https://cdsarc.cds.unistra.fr/ftp/J/ApJ/885/74/table1.dat),
data row 22, contains **the same intended name and numeric Gaia ID**, with
coordinates RA **3.98905°**, Dec **+18.50957°**. The companion
[table 4](https://cdsarc.cds.unistra.fr/ftp/J/ApJ/885/74/table4.dat), row 15,
links the corresponding short name `J0015+1830` to 7,346 ± 417 K and the
reported hydrogen value. The [CDS metadata](https://cdsarc.cds.unistra.fr/ftp/J/ApJ/885/74/ReadMe)
specifies J2000 coordinates and Gaia DR2 identifiers in that original table.

The direct Gaia DR3 query confirms the same numeric ID at RA
**3.989053625°**, Dec **+18.509564561°**, only **0.196 arcseconds** from the
full name. It is about **12.67 degrees** from the PEWDD RA/Dec fields.
This is a coordinate-field conflict; it is not evidence that this row's Gaia
ID is incorrect. The complete set of elemental measurements has not been
independently revalidated in this audit.

## Epochs, aliases and the remaining uncertainty

For the first two cases, the separation between the *tabulated PEWDD
position* and its *assigned Gaia 2016 position* is only 0.640 and 0.777
arcseconds. These match the scales expected from their Gaia proper motions
over 16 years. The disagreement with the intended name is instead measured
in degrees. A coordinate-epoch conversion can explain those sub-arcsecond
position offsets but cannot reconcile these two stellar identities. The
third case has the assigned ID, original-paper name and direct Gaia position
in agreement, with only the PEWDD position fields elsewhere.

The alternative names are traceable to different rows in the original
papers; this is not a case where two harmless aliases describe the same
source. No inference about the database's update code, join algorithm or
maintainers is needed to establish these particular serialized conflicts.

The appropriate downstream rule is to hold the flagged associations for
source review and resolve the name, original-paper row, Gaia source and
coordinate epoch together. Some cases may need a new association; others
may require only corrected coordinates. **Three verified examples cannot
supply the correction or error-class breakdown for all 236 flagged rows.**
The diagnosis here applies to the stated snapshot, not automatically to
subsequent releases or the live service.
