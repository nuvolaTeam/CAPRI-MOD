********************************************************************************
$ontext

   CAPRI project

   GAMS file : biofuel_technology_params.gms

   @purpose  : Define conversion coefficients for biofuels and biofuel by-products
   @author   : W.Britz, A.Becker, M.Blanco
   @date     : 15.05.13
   @since    : 2007
   @refDoc   :
   @seeAlso  :
   @calledBy : baseline\load_aglink.gms, global\biofuel_markets.gms

$offtext
********************************************************************************

* ---  Conversion coefficients for 1st generation biofuel production (t/t)
*      Source: RED 2009 and Aglink data (values for 2005)
*      Aglink assumptions based on OECD study Agricultural market impacts of future
*      growth in the production of biofuels (Table 3.1, page 41)

parameter p_ExtrRates(*,*) "Conversion rates biofuel from feedstock" /
     BIOE. WHEA  0.283
     BIOE. SWHE  0.283
     BIOE. DWHE  0.283
     BioE. MAIZ  0.309
** corse grains are set lower than wheat
     BioE. RYEM  0.283
     BioE. BARL  0.283
     BioE. OATS  0.283
     BioE. OCER  0.283

     BioE. SUGA  0.478
     BioE. TWIN  0.100

** sugarbeet: assuming a conversion rate from beet to sugar of 0.16
     BioE. SUGB  0.076

     BioD .RAPO  0.959
     BioD .SUNO  0.959
     BioD .SOYO  0.959
     BioD .OLIO  0.959
     BioD .OTHO  0.959
     BioD .PLMO  0.959
     /;

* ---  Conversion coefficients for biofuel by-products (t/t)
*      Source: RED 2009 and Aglink data (values for 2005)

parameter p_ByProduct(*,*) "processing coefficient per ton of product converted to bio fuel" /
*** DDGS Coefficients
     DDGS.WHEA  0.371
     DDGS.SWHE  0.371
     DDGS.DWHE  0.371
     DDGS.MAIZ  0.313
     DDGS.RYEM  0.371
     DDGS.BARL  0.371
     DDGS.OCER  0.371
     DDGS.OATS  0.371
*** Glycerine coefficients
     GLYC.RAPO  0.100
     GLYC.SUNO  0.100
     GLYC.SOYO  0.100
     GLYC.OLIO  0.100
     GLYC.OTHO  0.100
     GLYC.PLMO  0.100
     /;

* ---  Conversion coefficients for biomass to ethanol or biodiesel (Tons of biofuel per dry ton of biomass)
*      Assumption: ARES (Grain straw and sugar beet leaves) and NECR (Poplar, willow, miscanthus)
*      can be used for the production of Fischer-Tropsch diesel and lignocellulosic ethanol
*      Source: JEC-WTW studies (http://iet.jrc.ec.europa.eu/about-jec/jec-well-wheels-analyses-wtw)

parameter p_secgConv "Conversion coefficients for biomass to biofuel (t/t)" /
     BIOE 0.147
     BIOD 0.195
     /;

* ---  energy content of transport fuels
*      Source: Data from RED 2009 (energy content per ton)

parameter p_oilEqu(rows) "oil equivalents of different fuel types"/
* 1t =   toe
  DISL  1.027
  GASL  1.027
  BIOD  0.884
  BIOE  0.645
        /;

* ---  density
*      Source: Data from RED 2009
*      note that the same conversion rates apply for thousand m3 --> tonnes
parameter p_density(rows) "density of liquids" /
* 1l =   kg
  DISL  0.837
  GASL  0.744
  BIOD  0.892
  BIOE  0.778
  CRDO  0.880
        /;

