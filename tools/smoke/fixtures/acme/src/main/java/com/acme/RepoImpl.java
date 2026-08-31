package com.acme;
public class RepoImpl implements Repo {
    public String find(String id) { return persist(id); }
    private String persist(String id) { return "ok"; }
}
