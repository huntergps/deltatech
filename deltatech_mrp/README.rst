===========================================
MRP Extension
===========================================
.. image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
   :alt: License: LGPL-3


Ajustari:

mrp.bom

    - adaugat campul value_overhead - procent pt cheltuieli indirecte
    - rotunjire cantitate la explozia BOM in conformitate cu definitia unitati de masura

mrp.production

    - modificat metoda action_confirm
        - modificare date_expected pentru miscarile generate de comanda de productie
        - generarea automata a unui lot de productie daca produsul este gestionat in loturi

mrp.production.product.line
    - adaugat camp cantitate disponibila
    - adaugat metoda onchange_product_id



Rapoarte:

deltatech.mrp.report
    - raport pt analiza costuri de productie

Observatie:
 - la costul materialelor se adauga si un coeficient de 20 % pentru costurile indirecte.




Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/dhongu/deltatech/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Credits
=======


Contributors
------------

* Dorin Hongu <dhongu@gmail.com>


Maintainer
----------

.. image:: https://apps.odoo.com/apps/modules/12.0/deltatech/logo-terrabit.png
   :alt: Terrabit
   :target: https://terrabit.ro

This module is maintained by the Terrabit.


