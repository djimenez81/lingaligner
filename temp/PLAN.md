# Initial Implementation Plan for the `lingaligner` Package

This could be consider an initial _planning board_ for the implementation of
this package.

The `lingaligner` package wants to be a library providing the user with a set
of classes and functionalities to perform phonetic alignment of cognates or
other corresponding terms within a user-provided, phonetically annotated
corpus, in an analogous manner as it is done with genetic or proteomic data.

## The Initial Plan

<!-- The Chibchan Pipeline -->

The first phase of this project constitutes the clean implementation of the
messy code that was used for the research published in
[this paper](https://semas.uaq.mx/index.php/ojs/article/view/123/229). The
steps to follow are:

1. Define the basic file manager class that allows to open the `xlsx` files
and import them as dataframes.
2. Define the `Corpus` and `PhoneticInventory` classes, with the methods to
initialize from the dataframes provided.
3. Define the methods to "_parse_" the items on `Corpus`.
4. Define the `Aligner` class with the methods for individual alignment.
5. Define the methods to compute the _Language Distance_ matrix.
6. Define the methods to compute the tree.

## Future Functionalities

- Provide functionalities for other types of files.
- Provide functionalities for multiple alignment.
- Provide functionalities to compute a `BLOSUM` style matrix. 
