package io.github.junzzu.leaselens.common;

public class NotFoundException extends RuntimeException {
    public NotFoundException(String entity, Object id) {
        super("No " + entity + " with id " + id);
    }
}
