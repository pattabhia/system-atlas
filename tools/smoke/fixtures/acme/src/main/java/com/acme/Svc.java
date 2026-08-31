package com.acme;
public class Svc {
    private Repo repo;                     // typed as the INTERFACE
    public String run(String id) {
        return repo.find(id);             // resolves to Repo.find -> must emit override edge to RepoImpl.find
    }
}
