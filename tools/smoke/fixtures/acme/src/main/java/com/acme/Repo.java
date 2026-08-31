package com.acme;
/** Non-MOSIP fixture: interface + impl + caller. Guards against target-package leak
 *  in the Stage-B override-edge index (interface->impl dispatch must work on ANY codebase). */
public interface Repo { String find(String id); }
